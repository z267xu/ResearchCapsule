# ResearchCapsule

> Read papers. Steal the good ideas. Leave the vibes in markdown.

This repo is a **shared snack drawer for research notes** — quick, opinionated summaries of papers about A/B testing, AI (prompt engineering, LLM-as-judge, agents), ML, measurement, calibration, and whatever else made someone go *"wait… that actually helps."*

No gatekeeping. No minimum citation count. If a paper is useful, weird, or sparkly enough to remember next week, it belongs here.

## What’s inside

Notes live in theme folders (create a new one if yours doesn’t fit):

| Folder | For papers about… |
|---|---|
| [`AB_tests/`](AB_tests/) | Experiments, surrogates, strategy iteration, online learning loops |
| [`Prompt_iteration/`](Prompt_iteration/) | Prompt / policy / rubric optimization |
| [`Label_quality/`](Label_quality/) | LLM-as-judge, consensus, hallucination filters, noisy labels |
| [`Calibration/`](Calibration/) | Probability calibration, multicalibration, confidence you can trust |

One paper → one markdown file. Filename = paper name (or a short recognizable title).

## Why this exists

Conference PDFs are long. Slack threads evaporate. Notebooks get lost.

ResearchCapsule is the middle ground: **enough detail to reuse the idea later**, short enough to skim over coffee. Prefer concrete examples over abstract praise. Prefer “how we’d use this” over “this paper is interesting.”

## Contribute (please do)

PRs welcome from anyone — teammate, friend, future-you-at-2am.

1. **Pick a paper** you actually read (or at least fought with).
2. **Drop a `.md`** in the right folder (or invent a folder if the taxonomy is wrong — taxonomy is not sacred).
3. **Write a short note** — see template below.
4. **Open a PR** with a title like `Add: HUMBR consensus filter` or `Add: A/B Agent Tree-RAG`.

That’s it. Perfect prose optional. Clarity mandatory. Hot takes encouraged if labeled as takes.

### Suggested note template

Steal this, remix it, ignore it — as long as a stranger can get value in ~3 minutes:

```markdown
# Paper Title

## Paper Link
https://...

## One-Line Summary
One sentence. No plot twists.

## Core Problem
What pain does this paper claim to fix?

## Method
How it works, in plain language. A tiny `text` diagram is welcome.

## Concrete Example
Walk through one toy / production-shaped example.
Inputs → what happens → outputs.

## Results
Only the headline numbers. Skip the appendix Olympics.

## Relation to Our Work (optional)
- Directly useful / adjacent / orthogonal
- Where it could plug in
- What we should *not* copy blindly

## Bottom Line
The one sentence you’d tattoo on a whiteboard.
```

### House style (light rules, heavy vibes)

- **Be accurate first**, funny second.
- Prefer **examples** over buzzwords.
- Call out **cost, failure modes, and “don’t import this blindly”**.
- Link the paper (arXiv / DOI / PDF).
- Don’t dump full PDFs into the repo unless there’s a good reason.
- If you’re unsure which folder: pick the closest one and mention alternatives in the PR.

## Not the goal

- A complete bibliography of humanity
- Peer-reviewed literature reviews
- Replacing reading the paper (sorry)

This is a **memory prosthetic with friends**.

## License / credit

Notes are contributed by humans who cared enough to write them down. When you borrow an idea into a design doc, keep the paper citation. When you borrow a joke… maybe don’t put it in the abstract.

---

**Got a paper that made you rethink an A/B metric, a judge prompt, or a calibration trick?**  
Add a note. Future us will high-five past us.
