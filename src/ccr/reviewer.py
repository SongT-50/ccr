"""Core CCR engine — the heart of Cross-Context Review."""

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
    REVIEWER_SYSTEM,
    REVIEWER_USER,
)


def _detect_artifact_type(path: str) -> str:
    """Detect artifact type from file extension."""
    ext = Path(path).suffix.lower()
    code_exts = {".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".rb", ".swift", ".kt"}
    paper_exts = {".tex", ".bib"}
    if ext in code_exts:
        return "code"
    elif ext in paper_exts:
        return "paper"
    else:
        return "document"


def _parse_finding(line: str, reviewer_id: int) -> Finding | None:
    """Parse a single finding line into a Finding object."""
    # Format: [SEVERITY] AXIS | Location | Description | Suggestion
    pattern = r"\[(\w+)\]\s*(\w+)\s*\|\s*(.+?)\s*\|\s*(.+?)(?:\s*\|\s*(.+))?"
    match = re.match(pattern, line.strip())
    if not match:
        return None

    severity_str, axis_str, location, description, suggestion = match.groups()

    try:
        severity = Severity(severity_str.lower())
    except ValueError:
        severity = Severity.INFO

    axis_map = {"FACT": Axis.FACT, "CONS": Axis.CONS, "CTXT": Axis.CTXT,
                "RCVR": Axis.RCVR, "MISS": Axis.MISS}
    axis = axis_map.get(axis_str.upper(), Axis.CTXT)

    return Finding(
        axis=axis,
        severity=severity,
        location=location.strip(),
        description=description.strip(),
        suggestion=(suggestion or "").strip(),
        reviewer_id=reviewer_id,
    )


def _parse_director_finding(line: str) -> Finding | None:
    """Parse director's consolidated finding."""
    # Format: [SEVERITY] AXIS | Location | Description | Suggestion | Agreed by: R1,R2
    pattern = (
        r"\[(\w+)\]\s*(\w+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
        r"\s*[Aa]greed\s+by:\s*(.+)"
    )
    match = re.match(pattern, line.strip())
    if not match:
        return _parse_finding(line, 0)

    severity_str, axis_str, location, description, suggestion, agreed = match.groups()

    try:
        severity = Severity(severity_str.lower())
    except ValueError:
        severity = Severity.INFO

    axis_map = {"FACT": Axis.FACT, "CONS": Axis.CONS, "CTXT": Axis.CTXT,
                "RCVR": Axis.RCVR, "MISS": Axis.MISS}
    axis = axis_map.get(axis_str.upper(), Axis.CTXT)

    # Parse agreed reviewers
    agreed_ids = []
    for part in agreed.split(","):
        part = part.strip().lstrip("R").lstrip("★").strip()
        if part.isdigit():
            agreed_ids.append(int(part))

    return Finding(
        axis=axis,
        severity=severity,
        location=location.strip(),
        description=description.strip(),
        suggestion=suggestion.strip(),
        reviewer_id=0,
        agreed_by=agreed_ids,
    )


class CCRReviewer:
    """Cross-Context Review engine.

    Implements the CCR protocol from Song (2026):
    1. PRODUCE: artifact is created (externally)
    2. EXTRACT: only the artifact is taken (no conversation history)
    3. REVIEW: N independent sessions review the artifact
    4. INTEGRATE: Director merges findings, resolves conflicts

    Each API call is a completely isolated session — no shared context,
    no anchoring bias, no sycophancy. This is the core CCR principle.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model: str | None = None,
        num_reviewers: int = 3,
        parallel: bool = True,
    ):
        self.backend: LLMBackend = create_backend(provider, model)
        self.num_reviewers = num_reviewers
        self.parallel = parallel
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def review_file(self, path: str, artifact_type: str | None = None) -> ReviewResult:
        """Review a file using CCR protocol."""
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
        """Review an artifact using the CCR protocol.

        Step 1: N independent reviewers each get ONLY the artifact
        Step 2: Director merges all reviews
        """
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        # Step 1: Independent reviews (parallel or sequential)
        raw_reviews = self._run_independent_reviews(artifact, artifact_type)

        # Step 2: Director integration
        findings = self._run_director(artifact, raw_reviews)

        total_cost = estimate_cost(
            self.backend.model_name,
            self._total_input_tokens,
            self._total_output_tokens,
        )

        return ReviewResult(
            artifact_path=artifact_path,
            findings=findings,
            num_reviewers=self.num_reviewers,
            model=self.backend.model_name,
            total_tokens=self._total_input_tokens + self._total_output_tokens,
            estimated_cost_usd=total_cost,
        )

    def _run_independent_reviews(
        self, artifact: str, artifact_type: str
    ) -> list[str]:
        """Run N independent review sessions. Each session is completely isolated."""
        extra = EXTRA_INSTRUCTIONS.get(artifact_type, "")
        user_prompt = REVIEWER_USER.format(
            artifact_type=artifact_type,
            artifact=artifact,
            extra_instructions=extra,
        )

        def do_review(reviewer_id: int) -> str:
            # Each call creates a brand new session — CCR core principle
            response = self.backend.chat(REVIEWER_SYSTEM, user_prompt)
            self._total_input_tokens += response.input_tokens
            self._total_output_tokens += response.output_tokens
            return f"=== Reviewer {reviewer_id} ===\n{response.content}"

        if self.parallel:
            results = [""] * self.num_reviewers
            with ThreadPoolExecutor(max_workers=self.num_reviewers) as executor:
                futures = {
                    executor.submit(do_review, i + 1): i
                    for i in range(self.num_reviewers)
                }
                for future in as_completed(futures):
                    idx = futures[future]
                    results[idx] = future.result()
            return results
        else:
            return [do_review(i + 1) for i in range(self.num_reviewers)]

    def _run_director(self, artifact: str, raw_reviews: list[str]) -> list[Finding]:
        """Director session: merge, validate, and rank findings."""
        reviews_text = "\n\n".join(raw_reviews)

        system = DIRECTOR_SYSTEM.format(num_reviewers=self.num_reviewers)
        user = DIRECTOR_USER.format(artifact=artifact, reviews=reviews_text)

        response = self.backend.chat(system, user)
        self._total_input_tokens += response.input_tokens
        self._total_output_tokens += response.output_tokens

        # Parse director output
        findings = []
        for line in response.content.split("\n"):
            line = line.strip()
            if line.startswith("["):
                finding = _parse_director_finding(line)
                if finding:
                    findings.append(finding)

        return findings
