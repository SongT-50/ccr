# Hacker News — Show HN Post

## Title

Show HN: CCR – LLMs miss 64.5% of errors reviewing their own output. Session isolation fixes it

## Body

LLMs have a well-documented blind spot: when asked to review what they just generated, they anchor on their own output and miss errors. Tsui (2025) measured this at a 64.5% miss rate.

CCR (Cross-Context Review) is a simple fix: instead of asking the same session to review, spin up N independent API calls — each one sees only the artifact, with zero conversation history. No shared context means no anchoring bias, no sycophancy.

```
pip install ccr-review
ccr review mycode.py
```

That gives you 3 independent reviewers + a director that consolidates findings. Takes ~30 seconds, costs ~$0.02 with Haiku.

**What the experiments show** (360 reviews, 30 artifacts, 150 ground-truth errors):

- F1: 28.6% vs 24.6% for same-context review (p=0.008)
- Critical error detection: 40% vs 29%
- Repeating the review in the same context doesn't help (SR2 ~ SR, p=0.11) — it's session isolation that matters, not repetition

The tool is model-agnostic (Claude, GPT, Gemini). The bias it addresses is structural — it exists regardless of which model you use.

Based on three papers: CCR [1], D-CCR [2] (proves multi-turn review actually hurts — false positives increase 62%), and HCCA [3] (hierarchical multi-agent verification). Total: 660+ experimental sessions.

[1] https://arxiv.org/abs/2603.12123
[2] https://arxiv.org/abs/2603.16244
[3] https://arxiv.org/abs/2603.21454

GitHub: https://github.com/SongT-50/ccr

MIT licensed. Python API also available. Gemini backend and GitHub Action coming next.
