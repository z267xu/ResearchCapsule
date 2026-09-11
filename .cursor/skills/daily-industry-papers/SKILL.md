---
name: daily-industry-papers
description: >-
  Find 1–2 industry research papers for ResearchCapsule and pitch them for
  review. Use when the user says daily papers, daily paper, find papers, or
  wants industry papers from tech companies before any summarization.
---

# Daily Industry Papers

Pitch only. Stop after the pitch. Summarize only after the user picks.

## What to find

**1–2 papers**, published or released by a tech company (or with a clear industry first-author / deployed-system story).

**Core themes (prefer):**

- A/B tests, surrogates, measurement, online learning
- Prompt / policy / rubric optimization
- LLM-as-judge, label quality, hallucination / consensus filters
- Calibration / confidence you can treat as probability

**Adjacent industry ML (allowed if strong):** recsys, ranking, eval infra, agent systems, ads, trust & safety, data quality, production ML platforms. Strong means at least one of: real deployment / scale numbers, a production constraint that shaped the method, or a stealable primitive for our loop.

Skip:

- Pure theory with no industry authors and no production story
- Papers already noted under `AB_tests/`, `Prompt_iteration/`, `Label_quality/`, `Calibration/`
- A second paper that is basically the same idea as the first pick

## Where to look

Scan in this order, then pick the best 1–2 (not the first 1–2):

1. List existing capsule `.md` files so you do not repeat them.
2. Recent industry tracks: KDD ADS, WWW Industry, RecSys Industry, SIGIR industry, NeurIPS/ICML workshops with company labs.
3. Company research surfaces: Meta, Google / DeepMind, Microsoft, Amazon, Apple, Netflix, LinkedIn, Uber, Airbnb, ByteDance / TikTok, OpenAI, Anthropic, Snap, Spotify, Pinterest, X.
4. arXiv (`cs.LG`, `cs.AI`, `cs.CL`, `cs.IR`, `stat.ML`) whose affiliations are industry.

If web search is thin, say so and pitch the strongest candidates you can verify, with links.

## Pitch format

Use today's date. Nothing else in the reply except the pitch.

```markdown
# Daily papers — YYYY-MM-DD

## 1. Title
- Team / company:
- Link:
- Why I picked it (2 sentences):
- Strength: core-theme | adjacent-but-strong
- Guessed folder: AB_tests | Prompt_iteration | Label_quality | Calibration | new?

## 2. Title
- Team / company:
- Link:
- Why I picked it (2 sentences):
- Strength: core-theme | adjacent-but-strong
- Guessed folder: ...

Reply: **1** / **2** / **both** / **neither + your papers**
```

Prefer 2. If only one paper is clearly good, send 1 and say why the second slot is empty.

## Hard stops

- Do not download or fully read the paper.
- Do not write a ResearchCapsule `.md`.
- Do not commit or push.
- If the user says neither and names other papers, switch to the summarizer skill on *those* papers.
