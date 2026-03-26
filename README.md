# CCR: Cross-Context Review

> **Eliminate LLM blind spots. Automatically.**

LLMs miss **64.5% of errors** when reviewing their own output ([Tsui, 2025](https://arxiv.org/abs/2502.13063)). CCR fixes this by running multiple **completely isolated** review sessions — no shared context, no anchoring bias, no sycophancy.

**One command. Three independent reviewers. 30 seconds. ~$0.02.**

```bash
pip install ccr-review
ccr review mycode.py
```

## The Problem

When you ask an LLM to "review what you just wrote," it's like asking someone to proofread their own essay — they see what they *meant* to write, not what they *actually* wrote.

This is not a model limitation. It's a **structural bias** that persists across GPT, Claude, Gemini, and every future model. As long as the reviewer shares context with the producer, blind spots are inevitable.

## The Solution

CCR (Cross-Context Review) breaks this cycle through **session isolation**:

```
Your Code ──→ [Reviewer 1] ──→
         ──→ [Reviewer 2] ──→  [Director] ──→ Consolidated Report
         ──→ [Reviewer 3] ──→

Each reviewer is a separate API call.
No shared memory. No anchoring. No sycophancy.
```

**Key research findings** (360 reviews, 30 artifacts, 150 ground-truth errors):
- CCR outperforms same-context review: **F1 28.6% vs 24.6%** (p=0.008)
- Critical errors show the largest gap: **40% vs 29%** detection rate
- Repeating reviews in the same context doesn't help (SR2 ≈ SR, p=0.11)
- **Session isolation is the key mechanism**, not repetition

## Quick Start

```bash
# Install
pip install ccr-review

# Set your API key (pick one)
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...

# Review code
ccr review mycode.py

# Review with more reviewers
ccr review mycode.py --reviewers 5

# Verify a research paper
ccr verify paper.tex

# Use a different model
ccr review app.js --provider openai --model gpt-4o

# See all models and pricing
ccr models
```

## Python API

```python
from ccr import CCRReviewer

reviewer = CCRReviewer(
    provider="anthropic",
    model="claude-haiku-4-5-20251001",  # ~$0.02/review
    num_reviewers=3,
)

result = reviewer.review_file("mycode.py")

print(result.summary())

# Consensus findings = agreed by 2+ independent reviewers
for finding in result.consensus_findings:
    print(f"[{finding.severity.value}] {finding.description}")
```

## How It Works

CCR implements the protocol from [Song (2026)](https://arxiv.org/abs/2603.12123):

| Step | What Happens | Why |
|------|-------------|-----|
| **Extract** | Only the artifact is taken | Removes conversation history = removes bias source |
| **Review** | N independent API calls review it | Each call has zero prior context |
| **Integrate** | Director merges all reviews | Consensus filtering reduces false positives |

### 5-Axis Verification Framework

Every review systematically covers:

| Axis | What It Checks |
|------|---------------|
| **FACT** | Factual accuracy — numbers, names, technical claims |
| **CONS** | Internal consistency — contradictions, terminology mismatches |
| **CTXT** | Contextual fitness — works in intended environment? |
| **RCVR** | Receiver perspective — could readers misunderstand? |
| **MISS** | Completeness — anything important missing? |

### Consensus Filtering

Not all findings are equal. When 2+ independent reviewers flag the same issue **without seeing each other's reviews**, it's almost certainly a real problem. These consensus findings are marked with ★.

## Model-Agnostic

CCR works with **any LLM**. The bias it eliminates is structural, not model-specific:

| Model | Per Review | Monthly (10/day) |
|-------|-----------|-------------------|
| GPT-4o mini | ~$0.01 | ~$3 |
| Gemini 2.5 Flash | ~$0.01 | ~$3 |
| Claude Haiku 4.5 | ~$0.05 | ~$15 |
| GPT-4o | ~$0.11 | ~$33 |
| Claude Sonnet 4.6 | ~$0.19 | ~$57 |

Run `ccr models` for current pricing.

## Research

CCR is based on peer-reviewed research with 660+ experimental sessions:

- **CCR**: [Cross-Context Review: Eliminating Anchoring Bias in LLM Self-Review](https://arxiv.org/abs/2603.12123) — The core method. Session isolation > repetition.
- **D-CCR**: [More Rounds, More Noise: Why Multi-Turn Review Fails](https://arxiv.org/abs/2603.16244) — Proves that repeating reviews *hurts* (FP +62%). One independent round is optimal.
- **HCCA**: [Hierarchical Cross-Context Aggregation](https://arxiv.org/abs/2603.21454) — Multi-agent architecture with intentional information restriction.

## Roadmap

- [x] Core CCR protocol (independent reviewers + director)
- [x] CLI (`ccr review`, `ccr verify`, `ccr models`)
- [x] Anthropic & OpenAI backends
- [ ] Google Gemini backend
- [ ] HCCA mode (hierarchical multi-agent verification)
- [ ] GitHub Action (auto-review on PR)
- [ ] CCR Benchmark dataset on HuggingFace
- [ ] VS Code extension

## License

MIT

## Citation

```bibtex
@article{song2026ccr,
  title={Cross-Context Review: Eliminating Anchoring Bias in LLM-Based
         Self-Review Through Context Isolation},
  author={Song, Tae-Eun},
  journal={arXiv preprint arXiv:2603.12123},
  year={2026}
}
```

---

**Built by [@SongT-50](https://github.com/SongT-50)** — Turning research into tools that work.
