# Hacker News — Show HN Post

## Title

Show HN: CCR – A small tool I built to catch errors LLMs miss when reviewing their own output

## Body

I've been learning about LLM code review and ran into a frustrating pattern: when you ask an LLM to review what it just wrote, it tends to agree with itself and miss obvious errors.

I dug into some research (Tsui, 2025) and found this is a known problem — LLMs miss about 64.5% of errors when reviewing in the same session, due to anchoring bias.

So I tried a simple idea: instead of reviewing in the same conversation, spin up separate API sessions that only see the output — no conversation history. It's called Cross-Context Review (CCR).

I ran some experiments (360 reviews) and the results were modest but statistically significant:
- F1 improved from 24.6% to 28.6% (p=0.008)
- Critical errors caught: 40% vs 29%
- Repeating in the same session didn't help (p=0.11) — isolation was the key

I packaged it into a small CLI tool:

```
pip install ccr-review
ccr review mycode.py
```

It runs 3 independent reviewers + a director that consolidates. Takes ~30s, costs ~$0.02 with Haiku.

Works with Claude, GPT, and Gemini — the bias is structural, not model-specific.

I wrote three papers while learning about this (all on arXiv), and I'd really appreciate any feedback from people who know more about this area:
- CCR: https://arxiv.org/abs/2603.12123
- D-CCR: https://arxiv.org/abs/2603.16244
- HCCA: https://arxiv.org/abs/2603.21454

GitHub: https://github.com/SongT-50/ccr

MIT licensed. Still learning and improving — any suggestions welcome.
