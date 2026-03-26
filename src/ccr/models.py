"""Data models for CCR review results."""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class Axis(Enum):
    """CCR 5+1 Axis Verification Framework."""
    FACT = "factual_accuracy"      # 사실 정확성
    CONS = "internal_consistency"  # 내부 일관성
    CTXT = "contextual_fitness"    # 맥락 적합성
    RCVR = "receiver_perspective"  # 수신자 관점
    MISS = "completeness"          # 완전성
    SEC = "security"               # 보안


@dataclass
class Finding:
    """A single review finding."""
    axis: Axis
    severity: Severity
    location: str          # line number or section
    description: str
    suggestion: str = ""
    reviewer_id: int = 0   # which independent reviewer found this
    agreed_by: list[int] = field(default_factory=list)  # cross-validation


@dataclass
class ReviewResult:
    """Aggregated CCR review result."""
    artifact_path: str
    findings: list[Finding] = field(default_factory=list)
    num_reviewers: int = 3
    model: str = ""
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def major_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MAJOR)

    @property
    def consensus_findings(self) -> list[Finding]:
        """Findings agreed by majority (2+ reviewers)."""
        return [f for f in self.findings if len(f.agreed_by) >= 2]

    def summary(self) -> str:
        lines = [
            f"CCR Review: {self.artifact_path}",
            f"Reviewers: {self.num_reviewers} independent sessions",
            f"Model: {self.model}",
            f"Findings: {len(self.findings)} total "
            f"({self.critical_count} critical, {self.major_count} major)",
            f"Consensus findings: {len(self.consensus_findings)} "
            f"(agreed by 2+ reviewers)",
            f"Estimated cost: ${self.estimated_cost_usd:.4f}",
        ]
        return "\n".join(lines)
