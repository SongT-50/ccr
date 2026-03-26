# Reddit r/MachineLearning Post

## Title

[P] CCR: Open-source tool that eliminates LLM self-review blind spots through session isolation (3 papers, 660+ experiments)

## Body

**TL;DR**: LLMs miss 64.5% of errors when reviewing their own output due to anchoring bias. CCR runs independent review sessions with no shared context, improving F1 from 24.6% to 28.6% (p=0.008). Now available as an open-source CLI tool.

---

### Background

There's a well-known problem with LLM self-review: when you ask a model to review what it just generated, it tends to agree with itself. This isn't a quirk of any specific model — it's a structural issue. The reviewer shares the same context as the producer, which introduces anchoring bias and sycophantic tendencies.

Tsui (2025) quantified this: LLMs fail to correct 64.5% of their own errors when the review happens in the same context. Repeating the review in the same session doesn't help either.

### The Method

CCR (Cross-Context Review) addresses this through a simple mechanism: **session isolation**. Instead of reviewing in the original session, the artifact is extracted and sent to N completely independent API sessions. Each reviewer sees only the artifact — no conversation history, no prior judgments.

The protocol:
1. **Extract** — Take only the final artifact from the production session
2. **Review** — N independent API calls review it (zero shared context)
3. **Integrate** — A director session consolidates findings, with consensus filtering

### Experimental Results

Across three studies totaling 660+ experimental sessions:

**CCR paper** (360 reviews, 30 artifacts, 150 ground-truth errors):
- CCR vs same-context review: F1 28.6% vs 24.6% (p=0.008, Cohen's d=0.40)
- Critical error detection: 40% vs 29%
- Same-context repeated review (SR2) shows no improvement over single review (p=0.11), confirming that session isolation — not repetition — is the active mechanism

**D-CCR paper** (300 sessions):
- Multi-turn review within the same context actually degrades quality: false positives increase by 62%
- One independent review round is optimal

**HCCA paper**:
- Hierarchical multi-agent architecture with intentional information restriction
- Extends CCR to structured multi-agent verification pipelines

### The Tool

```bash
pip install ccr-review
ccr review mycode.py          # 3 independent reviewers, ~30s, ~$0.02
ccr review app.js --reviewers 5
ccr verify paper.tex
```

Model-agnostic — works with Claude, GPT, Gemini. The bias is structural, not model-specific.

Python API:

```python
from ccr import CCRReviewer

reviewer = CCRReviewer(provider="anthropic", num_reviewers=3)
result = reviewer.review_file("mycode.py")

for finding in result.consensus_findings:
    print(f"[{finding.severity.value}] {finding.description}")
```

### Links

- GitHub: https://github.com/SongT-50/ccr
- CCR paper: https://arxiv.org/abs/2603.12123
- D-CCR paper: https://arxiv.org/abs/2603.16244
- HCCA paper: https://arxiv.org/abs/2603.21454

MIT licensed. Feedback and contributions welcome.

### Roadmap

- Gemini backend
- GitHub Action for auto-review on PRs
- HCCA mode (hierarchical multi-agent)
- Benchmark dataset on HuggingFace
