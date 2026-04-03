# Reddit r/MachineLearning Post

## Title

[P] CCR: A small tool I built to help LLMs catch more errors by reviewing in isolated sessions

## Body

**TL;DR**: I noticed LLMs miss a lot of errors when reviewing their own output, so I tried running reviews in separate sessions with no shared context. It helped. I packaged it as an open-source tool and wanted to share what I learned.

---

### What I noticed

While using LLMs for coding, I kept running into the same issue: asking the model to review what it just generated didn't catch much. It would say "looks good" even when there were clear problems.

I found some research (Tsui, 2025) showing this is a known bias — LLMs fail to correct about 64.5% of errors when reviewing in the same context. It's anchoring bias: the reviewer shares context with the producer.

### What I tried

The idea is simple: instead of reviewing in the original session, extract the output and send it to completely new API sessions. Each reviewer sees only the artifact — no conversation history, no prior judgments.

I call it Cross-Context Review (CCR).

### What the experiments showed

I ran 360 reviews across 30 artifacts with 150 ground-truth errors:

- CCR vs same-context: F1 28.6% vs 24.6% (p=0.008, d=0.40)
- Critical error detection: 40% vs 29%
- Repeating in the same session (SR2) didn't help (p=0.11)
- In a follow-up study (D-CCR), multi-turn review actually made things worse — false positives went up 62%

The improvements are modest, but the finding that isolation matters more than repetition was interesting to me.

### The tool

```bash
pip install ccr-review
ccr review mycode.py
```

Runs 3 independent reviewers + a director. ~30 seconds, ~$0.02 with Haiku. Works with Claude, GPT, and Gemini.

Python API:

```python
from ccr import CCRReviewer

reviewer = CCRReviewer(provider="anthropic", num_reviewers=3)
result = reviewer.review_file("mycode.py")
```

### Links

- GitHub: https://github.com/SongT-50/ccr
- CCR paper: https://arxiv.org/abs/2603.12123
- D-CCR paper: https://arxiv.org/abs/2603.16244
- HCCA paper: https://arxiv.org/abs/2603.21454

MIT licensed. I'm still learning a lot about this area, so I'd really appreciate any feedback or suggestions from people with more experience. Thanks for reading.
