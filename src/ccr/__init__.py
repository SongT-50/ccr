"""CCR: Cross-Context Review — Model-agnostic LLM bias elimination."""

__version__ = "0.1.0"

from ccr.reviewer import CCRReviewer
from ccr.models import ReviewResult, Finding

__all__ = ["CCRReviewer", "ReviewResult", "Finding"]
