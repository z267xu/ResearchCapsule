# PCap: Personalized Retrieval-Stage Diversity Capping in Facebook Marketplace (Marketplace, Meta)

## Paper Link
https://arxiv.org/abs/2609.16452

## Marketplace logic (read this first)

**Marketplace** is a scroll of used stuff for sale (phones, couches, cars). Retrieval is the first cut: many **sources** (ANN, i2i, …) each dump a pile of listings. Ranking only sees what retrieval kept.

If everyone last week clicked phones, every source over-fetches phones. The ranker never gets a fair shot at furniture. **Cap** = “from this category, at most $N$ listings in this pile.”

People are not equal. Phone-only shoppers want a **relaxed** cap (more phones). Browsers who click many categories want a **tight** cap (force mix). Loose = the ceiling $N$ is high (less diversity pressure). Tight = $N$ is low (more diversity pressure). PCap puts you in one of six **diversity buckets** from recent clicks, then sets $N$ per bucket.

## One-Line Summary
At retrieval, cap how many items each category may contribute, with a looser cap for focused shoppers and a tighter cap for diverse browsers — uniform diversity only buys extra views, not extra clicks.

## Core Problem
Past clicks feed more of the same. Diversity at **ranking** (MMR, DPP) needs a global scored list; retrieval is sharded, over-fetched, and has no global score. A single cap for everyone raises browsing but not purchase-shaped actions. Offline replay misses the second-order effect (new mix $\to$ ranker $\to$ session).

## Terminology

| Symbol | Plain meaning |
|---|---|
| FPT | Facebook Product Taxonomy: phones, cars, furniture, … |
| $p(c\mid u)$ | Share of user $u$’s recent Marketplace clicks in category $c$. |
| $S(u)$ | Shannon entropy of that click mix. High = historically diverse. |
| $d_u$ | $S(u)$ min–max scaled to $[0,1]$. |
| Buckets 1–6 | 1 = most focused, 6 = most diverse. Even counts, stable day to day. |
| $m_u$ | Multiplier on the category cap for that bucket. |
| $f_k$ | Extra multiplier per retrieval source $k$. |
| Uniform capping | One rule: buyers vs non-buyers. Not six entropy buckets. |
| PTS | Parameter Tuning Sequence: sequential live grid search that shrinks the $m_u$ range. |
| VPV / PDP / MLI | Views / detail-page clicks / buyer–seller message with a reply. |

Cap rule of thumb (from live PTS, not a formula they claim as theory):

```text
bucket 1–2  focused   larger m_u   relaxed cap   more of one category
bucket 3–4  middle    m_u ≈ 1      leave it
bucket 5–6  diverse   smaller m_u  tight cap     force other categories
```

$$
S(u) = -\sum_{c} p(c\mid u)\log p(c\mid u).
$$

HHI was their old diversity number; it ignores *how many* clicks. Four categories once vs ten categories once both look “max diverse.” Entropy + click volume is why they switched for **bucketing**. They still **report** HHI on the feed because that is what QE already logs.

## Method
Group listings by FPT. At shard scan and at aggregation, keep at most $\mathrm{cap}(u,k,c)$ from category $c$. Cap $\propto$ source fetch $\times f_k \times m_u$.

Do not hand-tune $m_u$. PTS: each arm is a vector of bucket multipliers; small traffic for $\ge$ one weekday+weekend; keep the envelope around winners; repeat. They use a grid on purpose (noisy metrics, existing QE arms), not a bandit.

Two-phase A/B only. No offline retrieval metric they trust.

```text
clicks last window → entropy → bucket 1..6
each retrieval source over-fetches
  → per-category cap(user bucket, source)
  → ranker sees a less phone-dominated pile
```

## Concrete Example
Alex clicks only “Cell Phones” this week $\to$ bucket 1 $\to$ relaxed cap $\to$ the pile can be mostly phones.

Sam clicks phones, furniture, cars, bikes $\to$ bucket 6 $\to$ tight cap $\to$ after ~$N$ phones the shard must pull other FPT groups.

Uniform “cap everyone a bit” is like forcing Sam’s mix onto Alex: more categories on screen (VPV up), Alex does not open PDPs.

Ask analog: do not apply one “show 20% adjacent topic” quota to every Ask session. Heavy AC-intents vs fashion-browsers need different caps at **candidate gen**, or the ranker never sees the mix.

## Results
Phase 1, uniform vs no cap:

```text
VPV     +0.31%   sig
PDP     +0.03%   n.s.
MLI     −0.26%   n.s.
sessions +0.05%  n.s.
latency +8.6 ms
```

Phase 2, PCap vs uniform (PTS-tuned $m_u$):

```text
VPV      +0.22%   sig
PDP      +0.23%   sig
MLI      +0.11%   n.s.
sessions +0.17%   sig
latency  +0.8 ms extra
```

Pagination diversity (HHI-style) moves as intended: bucket-1 **−1.05%** (more concentrated), bucket-6 **+0.25%**. Middle buckets barely move. Their slogan: personalization is **edge-heavy**.

## Relation to Our Work
- **Adjacent** to A/B / measurement, sibling to PinDCO. PinDCO taxes **pixels** of one creative. PCap taxes **slots per category** in the retrieval pile. Both: a local CTR/relevance greedy eats the page; a cap/tax is the serve-time fix. Offline replay lied; they only believe live A/B (and PTS).
- Different from Chou: this is not blending two experiment metrics. PTS *is* an online search over policy knobs, closer to “how we pick $\theta$” than to north-star blending.
- Uniform diversity is the always-average policy: more impressions, no deeper action. Same warning as a global prevalence bucket that hides slices (MCGrad’s cancelling subgroups).
- Do **not** import blindly: entropy of **clicks** is not true preference (exposure-biased); six buckets and FPT are Marketplace-specific; +0.2% PDP is a large-N win; they refused Bayesian opt because QE is fixed-allocation. Retrieval cap cannot fix a ranker that still sorts phones first.

## Bottom Line
A diversity cap at retrieval only pays off if focused users get a loose cap and explorers get a tight one. One cap for everyone buys extra scrolling, not extra intent.
