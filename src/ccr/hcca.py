"""HCCA engine — Hierarchical Cross-Context Aggregation.

Extends CCR with a 4-layer hierarchical review structure:
  Layer 1 (Workers):   N independent analyses (same as CCR reviewers)
  Layer 2 (Verifiers): Cross-verification of worker findings
  Layer 3 (Director):  Integration and conflict resolution
  Layer 4 (Meta):      Final quality gate

Key principle: "Intentional Information Restriction" — each layer
receives only the information it needs, nothing more.

Reference: Song (2026) "HCCA" arXiv:2603.21454
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ccr.backends import LLMBackend, create_backend, estimate_cost
from ccr.models import Axis, Finding, ReviewResult, Severity
from ccr.prompts import (
    DIRECTOR_SYSTEM,
    DIRECTOR_USER,
    EXTRA_INSTRUCTIONS,
    META_SYSTEM,
    META_USER,
    REVIEWER_SYSTEM,
    REVIEWER_USER,
    VERIFIER_SYSTEM,
    VERIFIER_USER,
)
from ccr.reviewer import _detect_artifact_type, _parse_director_finding, _parse_finding


class HCCAReviewer:
    """Hierarchical Cross-Context Aggregation reviewer.

    4-layer architecture where each layer operates under intentional
    information restriction — seeing only what it needs to do its job.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model: str | None = None,
        num_workers: int = 3,
        parallel: bool = True,
    ):
        self.backend: LLMBackend = create_backend(provider, model)
        self.num_workers = num_workers
        self.parallel = parallel
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def review_file(self, path: str, artifact_type: str | None = None) -> ReviewResult:
        """Review a file using the HCCA protocol."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        artifact = file_path.read_text(encoding="utf-8")
        if not artifact_type:
            artifact_type = _detect_artifact_type(path)

        return self.review(artifact, artifact_type=artifact_type, artifact_path=path)

    def review(
        self,
        artifact: str,
        artifact_type: str = "general",
        artifact_path: str = "<stdin>",
    ) -> ReviewResult:
        """Review an artifact using the full HCCA 4-layer protocol.

        Layer 1: N independent workers (identical to CCR reviewers)
        Layer 2: Cross-verification (Worker i's findings verified by Verifier j)
        Layer 3: Director integration (merge + conflict resolution)
        Layer 4: Meta review (final quality gate)
        """
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        # Layer 1: Independent workers
        raw_reviews = self._layer1_workers(artifact, artifact_type)

        # Layer 2: Cross-verification
        verified_reviews = self._layer2_verifiers(artifact, artifact_type, raw_reviews)

        # Layer 3: Director integration
        director_output, findings = self._layer3_director(artifact, verified_reviews)

        # Layer 4: Meta review
        findings = self._layer4_meta(artifact, director_output, findings)

        total_cost = estimate_cost(
            self.backend.model_name,
            self._total_input_tokens,
            self._total_output_tokens,
        )

        return ReviewResult(
            artifact_path=artifact_path,
            findings=findings,
            num_reviewers=self.num_workers,
            model=self.backend.model_name,
            total_tokens=self._total_input_tokens + self._total_output_tokens,
            estimated_cost_usd=total_cost,
        )

    # ------------------------------------------------------------------
    # Layer 1: Workers (independent review, same as CCR)
    # ------------------------------------------------------------------

    def _layer1_workers(self, artifact: str, artifact_type: str) -> list[str]:
        """Layer 1: N independent workers each review the artifact in isolation."""
        extra = EXTRA_INSTRUCTIONS.get(artifact_type, "")
        user_prompt = REVIEWER_USER.format(
            artifact_type=artifact_type,
            artifact=artifact,
            extra_instructions=extra,
        )

        def do_review(worker_id: int) -> str:
            response = self.backend.chat(REVIEWER_SYSTEM, user_prompt)
            self._total_input_tokens += response.input_tokens
            self._total_output_tokens += response.output_tokens
            return f"=== Worker {worker_id} ===\n{response.content}"

        if self.parallel:
            results = [""] * self.num_workers
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = {
                    executor.submit(do_review, i + 1): i
                    for i in range(self.num_workers)
                }
                for future in as_completed(futures):
                    idx = futures[future]
                    results[idx] = future.result()
            return results
        else:
            return [do_review(i + 1) for i in range(self.num_workers)]

    # ------------------------------------------------------------------
    # Layer 2: Verifiers (cross-verification)
    # ------------------------------------------------------------------

    def _layer2_verifiers(
        self, artifact: str, artifact_type: str, worker_reviews: list[str]
    ) -> list[str]:
        """Layer 2: Cross-verify worker findings.

        Each Worker i's findings are verified by Verifier (i+1 mod N).
        The verifier sees ONLY the artifact and that worker's findings —
        not any other worker's output.
        """

        def do_verify(worker_id: int, verifier_id: int) -> str:
            user_prompt = VERIFIER_USER.format(
                worker_id=worker_id,
                artifact_type=artifact_type,
                artifact=artifact,
                worker_findings=worker_reviews[worker_id - 1],
            )
            response = self.backend.chat(VERIFIER_SYSTEM, user_prompt)
            self._total_input_tokens += response.input_tokens
            self._total_output_tokens += response.output_tokens
            return (
                f"=== Verification of Worker {worker_id} "
                f"by Verifier {verifier_id} ===\n{response.content}"
            )

        # Build verification assignments: worker i verified by verifier (i%N)+1
        assignments = []
        for i in range(self.num_workers):
            worker_id = i + 1
            verifier_id = (i % self.num_workers) + 1  # circular assignment
            # Verifier must differ from worker
            if self.num_workers > 1:
                verifier_id = ((i + 1) % self.num_workers) + 1
            assignments.append((worker_id, verifier_id))

        if self.parallel:
            results = [""] * len(assignments)
            with ThreadPoolExecutor(max_workers=len(assignments)) as executor:
                futures = {
                    executor.submit(do_verify, wid, vid): idx
                    for idx, (wid, vid) in enumerate(assignments)
                }
                for future in as_completed(futures):
                    idx = futures[future]
                    results[idx] = future.result()
            return results
        else:
            return [do_verify(wid, vid) for wid, vid in assignments]

    # ------------------------------------------------------------------
    # Layer 3: Director (integration)
    # ------------------------------------------------------------------

    def _layer3_director(
        self, artifact: str, verified_reviews: list[str]
    ) -> tuple[str, list[Finding]]:
        """Layer 3: Director merges verified findings.

        The Director sees the artifact + all verification reports,
        but NOT the raw worker reviews (intentional information restriction).
        """
        reviews_text = "\n\n".join(verified_reviews)

        system = DIRECTOR_SYSTEM.format(num_reviewers=len(verified_reviews))
        user = DIRECTOR_USER.format(artifact=artifact, reviews=reviews_text)

        response = self.backend.chat(system, user)
        self._total_input_tokens += response.input_tokens
        self._total_output_tokens += response.output_tokens

        findings = []
        for line in response.content.split("\n"):
            line = line.strip()
            if line.startswith("["):
                finding = _parse_director_finding(line)
                if finding:
                    findings.append(finding)

        return response.content, findings

    # ------------------------------------------------------------------
    # Layer 4: Meta-reviewer (final quality gate)
    # ------------------------------------------------------------------

    def _layer4_meta(
        self, artifact: str, director_output: str, director_findings: list[Finding]
    ) -> list[Finding]:
        """Layer 4: Meta-reviewer evaluates the review itself.

        Sees the artifact + Director output only. Checks for:
        - False positives / hallucinated issues
        - Severity calibration
        - Completeness
        - Actionability
        """
        user = META_USER.format(
            artifact=artifact,
            director_review=director_output,
            num_workers=self.num_workers,
            num_verifiers=self.num_workers,
        )

        response = self.backend.chat(META_SYSTEM, user)
        self._total_input_tokens += response.input_tokens
        self._total_output_tokens += response.output_tokens

        # Try to parse FINAL FINDINGS from meta output
        meta_findings = self._parse_meta_output(response.content)

        # If meta produced usable findings, use them; otherwise keep director's
        if meta_findings:
            return meta_findings
        return director_findings

    def _parse_meta_output(self, content: str) -> list[Finding]:
        """Parse the Meta-reviewer's FINAL FINDINGS section."""
        findings: list[Finding] = []

        # Look for FINAL FINDINGS section
        in_final = False
        for line in content.split("\n"):
            stripped = line.strip()
            if "FINAL FINDINGS" in stripped.upper():
                in_final = True
                continue
            if in_final and stripped.startswith("["):
                finding = _parse_director_finding(stripped)
                if finding:
                    findings.append(finding)
            # Stop if we hit QUALITY SCORE (end of findings)
            if in_final and stripped.upper().startswith("QUALITY SCORE"):
                break

        return findings
