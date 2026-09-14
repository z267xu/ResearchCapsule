# As It Was: Aligning LLM Search Evaluation with Historical User Preferences (Search / Tech Research, Spotify)

## Paper Link
https://arxiv.org/abs/2607.01040

## Spotify search logic (read this first)

You do not need a Spotify account. **Search** is the box at the top: you type words, Spotify shows a page of songs / albums / playlists. That page is a **SERP**. Spotify keeps changing which song sits at #1. Someone has to grade: is this page good for this query?

Humans can do that. They are slow. Ranking changes every week, in many languages, including rare queries. So Spotify asks an **LLM judge**: here is the query, here are the result titles, is the page relevant?

That judge has a brain full of Wikipedia. On a clean query (`"adore you miley"`) it is fine. On a messy query it **guesses the intent**:

```text
You type:  when you say you love me
You meant: the lyric in Miley’s Adore You (you forgot the title)
LLM thinks: I need a track with exactly that title
            there isn’t one → this page looks bad
Users last month: people who typed almost the same words
                  kept playing Adore You → this page is good
```

**The problem this paper solves:** the judge’s world knowledge is not the same as **what Spotify users meant**. If you ship a ranking because the LLM liked it, you can ship the wrong page for lyric fragments, shared titles, and regional slang.

Logs already saw those similar old queries. You cannot dump raw clicks into the judge (everyone clicks #1 because it is #1). So they build a short **cheat sheet** per result and paste it into the prompt. That sheet is **QRI**:

| Letter | Full word | Plain meaning |
|---|---|---|
| Q | Query | A **similar old search** (not today’s query). |
| R | Relevance | After correcting for “it was sitting at #1,” did people actually engage this song for that old search? A number, not a vibe. |
| I | Impressions | How many times they **saw** it. So you know if R came from 12 people or 12,000. |

One QRI **line** looks like: *old query → (debiased relevance, how often shown)*. A **card** is a handful of those lines (cap 10) stuck next to one result. The prompt says: this is **evidence**, not the grade for today’s query.

**What QRI is not.** It is a log lookup, then a tiny paste into a **judge**. It is not “LLM reads the whole dictionary and returns the best song.”

```text
Already happened:  ranking model built a page of 3–5 songs
Then:              for each song on that page, fetch ~10 similar old queries
                   paste those lines next to the song
LLM job:           grade this page  0 / 0.5 / 1
                   (bad / partial / good). It does not reorder or pick #1.
```

**Debiased** = they already tried to undo position bias (IPS). Still not “true intent.” Just “what users did, less polluted by slot.”

**Plain judge (P)** = query + titles only. **Behavior-grounded (BG)** = P + the QRI cards.

## One-Line Summary
When the query is messy, do not let the LLM invent what it meant. Hand it last month’s debiased “similar query → this song, n times” card (QRI) and still let it grade today’s page.

## Core Problem
Ranking outruns human QA. A plain LLM judge scores the SERP from the query + metadata + world knowledge. Fine for crisp queries. Wrong on lyric fragments, overloaded titles, and regional readings — it invents intent.

Logs know how similar queries were engaged. Raw clicks are position-biased, and past clicks are not a label for this query. The move: a **small empirical prior** in the prompt, citeable, not ground truth.

## Terminology

| Symbol | Meaning |
|---|---|
| $q$ | Evaluation query. |
| $q'$ | A historical query, $q' \ne q$. |
| $e$ | A SERP entity / item. |
| $y \in \{0, 0.5, 1\}$ | Graded relevance the judge assigns. |
| $\hat{r}(e, q')$ | IPS-debiased historical relevance of $e$ for $q'$. |
| $I(e, q')$ | Historical impressions of $e$ under $q'$. |
| $k$ | Cap on QRI lines per item (paper: $k=10$). |
| P | **Plain** judge: query + locale + titles. No QRI. |
| BG | **Behavior-grounded** judge: same LLM and rubric as P, plus the QRI cards. Not a second model family. |
| DCG | **Discounted cumulative gain**: one number for the whole page. Sum item scores, but #1 counts more than #5 (users look at the top first). |

## Method
Same rubric, same $y \in \{0, 0.5, 1\}$ grades, same prompt skeleton. Two judges:

```text
Plain (P)   query + locale + item metadata
BG          P + one QRI card per result
```

**QRI line** for a historical query $q' \ne q$ and entity $e$:

$$
\{ q': (\hat{r}(e, q'), I(e, q')) \}.
$$

$\hat{r}$ is IPS-debiased relevance (position propensity from a randomized experiment or a monotonic click model). $I$ is impressions. Many $q'$ can attach to $e$; keep the top $k=10$ by semantic similarity to $q$ so popular entities do not eat the prompt.

Prompt says: QRI is **supporting context**, not the label for this query.

**Leakage (eval only).** Drop historical queries with cosine > 0.9 to the eval query (`"basketball warmup music"` drops `"basketball warmup playlist"`, keeps `"basketball training music"`). Production keeps near-duplicates. Logs used for QRI are from the month **before** the eval window.

When it helps (they claim three recurring patterns, not a uniform score bump):

```text
ambiguity     lyric / overloaded title  →  QRI picks the entity users actually played
severity      missing the demanded track →  BG fails harder than P
ranking       original vs re-record      →  BG penalizes the historically unloved #1
```

Clear queries: QRI is confirmatory, not decisive.

## Concrete Example
Query: `"when you say you love me"`.

```text
Plain judge:
  treats it as a title search
  SERP has no track with that exact title
  → low / partial relevance

QRI on the SERP items:
  similar lyric queries show high debiased r̂ + impressions
  on Miley Cyrus — Adore You

BG:
  users treat this as a lyric search
  SERP with Adore You → higher grade
```

Near-miss: `"dark til daylight"`. P gives partial credit for “thematically related” rows. QRI shows the Morgan Wallen track of that title is what users want and substitutes get little engagement → BG **fails** the page.

## Results
**Logs.** ~5,000 mid-frequency queries, recomposed 3–5 item SERPs → 5,965 pages. Each item has a debiased log score $\hat{r}$. **DCG** folds those into one page score (top slots weighted more). They then ask: does the judge’s page grade move with that DCG? (Spearman.) P vs BG is “same judge, no card vs with card.”

| Set | n | Spearman P | Spearman BG |
|---|---|---|---|
| All | 5965 | 0.416 | **0.438** (~+5%) |
| Flipped (P ≠ BG) | 918 | 0.147 | **0.281** (~+91% relative) |
| Equal | 5047 | 0.457 | 0.371 (BG not needed) |

**Human, 5 languages (HJM).** 265 SERPs. All: 0.450 → **0.516** (~+15%). Flipped (n=27): P **−0.127**, BG **0.530**. Absolute correlation stays moderate.

**Online.** One-week A/B, 904 queries, 3 SERPs per model, QRI from the month ending a week earlier. Sign alignment with the live winner: P **30.6%** → BG **36.8%** (`p < 0.01`). Still a coin-plus. BG only becomes directionally consistent with the online winner once a SERP has enough QRI support (`qri_count ≥ 5`, significant by ≥ 9). Sparse / cold-start: BG falls back to semantics.

## Bottom Line
When the query is ambiguous, do not let the LLM invent the intent. Hand it a short, debiased, citeable card of what users did last month — and still do not treat that card as the answer.
