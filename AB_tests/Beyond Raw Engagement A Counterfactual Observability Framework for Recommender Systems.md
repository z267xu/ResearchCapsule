# Beyond Raw Engagement: A Counterfactual Observability Framework for Recommender Systems (RecSys, Netflix)

## Paper Link
https://arxiv.org/abs/2609.22747

## Netflix logic (read this first)

You do not need a Netflix account. **Home** is a stack of **rows** (“Because you watched…”, “Trending”). Each row is a curated or ranked list of titles. A title near the left gets more eyes. A click on *Wednesday* can mean “great show,” “the row put it first,” or “the model loves it this week.” Raw views/CTR mix those.

Netflix already has an **Exploration & Exploitation** module that sometimes shows a title **on purpose with a logged chance** $\pi$. Those chances are the receipts. Without them you cannot unmix the pile.

**Counterfactual** here is not “would this user have streamed anyway” (Spotify holdback). It is: **if we delete this title / this row / this model decision, and the ranker fills the hole with the next-best thing, how much engagement do we lose?** That leftover is incrementality. A replaceable hit is not worth much. A title the substitute cannot replace is.

Same logs serve two desks: **creators** (is this row/title worth the slot?) and **modelers** (did the ranker or a label bug move the number?).

## One-Line Summary
Treat Home observability as leave-one-out incrementality from exploration logs: what engagement remains after the ranker substitutes, not raw CTR.

## Core Problem
Creators and modelers only see views/clicks. Those are biased by position and by whichever model is live. A good title can look dead because a new ranker buried it. A loud title can look incremental when a substitute would have gotten the same play. Cascades make it worse: retrieval already dropped the item, so ranking CTR is not “content quality.” Offline they want this answer **without** an A/B every time they edit a row.

## Terminology

| Symbol | Plain meaning |
|---|---|
| $x_j$ | Context of impression $j$ (user / page / slot). |
| $a_j$, $\pi_0$ | Arm shown; the logging (exploration) policy. |
| $\pi_e$ | Target policy we reweight to (current ranker, or leave-one-out). |
| $r_j$ | Reward on that impression (click / CTR, or a longer retention-style reward). |
| $m_j$ | 1 if $\pi_e$ would have shown this same $a_j$ in $x_j$, else 0. Drops rows that are not the target policy. |
| $w_j$ | $m_j / \pi_0(a_j \mid x_j)$. Rare shows get large weight. |
| SNIPS | Weighted-average CTR of $\pi_e$ from $\pi_0$ logs: $\sum r_j w_j / \sum w_j$. Not a new experiment. |
| Relativity | This title vs other titles **at the same position** (kills presentation bias). |
| Leave-one-out | Simulated policy: item $i$ is gone; the next-best arm takes its place. |
| Irreplaceability$(i)$ | Extra reward **given $i$ was eligible** (Hájek IPS they ship). |
| Universality$(i)$ | Share of sessions where $i$ is even a candidate. |
| Incrementality$(i)$ | Irreplaceability $\times$ Universality. Niche gem vs everywhere-OK. |
| Row curator | Human who builds a Home row. |

## Method
Need logged $\pi$. Then three measurements on the same foundation:

```text
bias reduction   SNIPS: reweight clicks so a rarely explored title is not punished
relativity       same-position SNIPS(this) − SNIPS(random eligible)
incrementality   SNIPS(full) − SNIPS(leave-one-out)   ← the headline
```

**SNIPS.** $\pi_0$ actually ran (we have $r_j$ and logged $\pi_0$). $\pi_e$ is the rule we wish we had run (greedy ranker, or leave-one-out). We do **not** rerun Home. We keep only rows $\pi_e$ would have shown ($m_j=1$) and upweight rare shows ($1/\pi_0$).

Vanilla IPS of one click shown with chance $0.1$: $r/\pi_0 = 1/0.1 = 10$ (“this rare show stands in for about 10 typical shows”). Summing those terms explodes if you over-sample tiny $\pi_0$. **Self-normalized** divides by the same weights, so the answer is a CTR in $[0,1]$:

$$
\mathrm{SNIPS} = \frac{\sum_j r_j w_j}{\sum_j w_j}, \qquad w_j = \frac{m_j}{\pi_0(a_j \mid x_j)}
$$

That is “reweight logged $r_j$ from $\pi_0$ onto $\pi_e$.” Clip tiny $\pi_0$ (they use a 10th-percentile floor; rows clip to $[0.0001, 0.9999]$).

Single-stage (one ranker, no cascade). Incrementality of item $i$ is the position-weighted lift of exploration vs the leave-one-out policy:

$$
\sum_{k=1}^{K} w_k \left( \mathrm{SNIPS}_{\mathrm{Exploration},k} - \mathrm{SNIPS}_{\mathrm{LOO},k} \right)
$$

Match $m=1$ only if the logged arm is the exploration top pick and is not $i$, or it is the second pick and the top pick **was** $i$. Else $m=0$. Cap tiny $\pi$ at the 10th percentile.

Cascade (retrieve $\to$ rank $\to$ rerank). Full leave-one-out is expensive, so they split:

$$
\mathrm{Incrementality}(i) = \mathrm{Irreplaceability}(i) \cdot \mathrm{Universality}(i)
$$

Irreplaceability = Hájek contrast of $r$ when $i$ was shown vs not, using logged $\pi$, only on sessions where $i$ was eligible. Universality = how often $i$ is eligible at all. Upstream modelers get a set-Jaccard leave-one-out on the **pool** (“did retrieval change the downstream list?”).

## Concrete Example

**SNIPS toy.** Four homes, slot 1. $\pi_e$ = leave-one-out *without Wednesday*: slot 1 should be *Slow Horses*.

```text
j   shown          r (click)   π_0    π_e would show this?   m    w=m/π_0   r·w
1   Wednesday      1           0.80   no                     0    0         0
2   Slow Horses    1           0.10   yes                    1   10        10
3   Slow Horses    0           0.10   yes                    1   10         0
4   Wednesday      0           0.80   no                     0    0         0
```

Raw CTR $= 2/4 = 50\%$. Mixes *Wednesday* and the slot; not “CTR if Wednesday is gone.” IPS sum $= 10$ (not a CTR). SNIPS $= (10+0)/(10+10) = 0.5$: among rows that **are** the leave-one-out slot, weighted CTR is $50\%$. Row 2 is rare, so it counts like 10 ordinary rows; row 3 the same, no click. Incrementality is $\mathrm{SNIPS}(\pi_0\text{ as-is}) - \mathrm{SNIPS}(\pi_e=\text{Wednesday deleted})$: two weighted CTRs, same logs, two $m$ rules.

**Leave-one-out on a row.** *New This Week* has *Wednesday* in slot 1. Raw CTR is high. Delete *Wednesday*, the row promotes *Slow Horses*. If people click *Slow Horses* almost as much, incrementality is small — the row was doing the work, not that title. If the row dies, incrementality is large.

Creator: ship the high-incrementality row idea without an A/B. Modeler: incrementality of title A drops while siblings stay flat $\to$ they found **positive labels on A were misattributed**, not “A got worse.”

Ask analog: raw “must-refuse rate” mixes policy, judge, and traffic mix. Need the exploration receipt (who was eligible) and a leave-one-out (“if we drop this pin / this A4 call, does the journey still fail?”). Do not treat raw volume as incremental harm.

## Results

```text
sim:     leave-one-out lift tracks true CTR loss when R1/R2 are deleted
         (gap grows with noise, still usable)
rows:    11 Home-row A/Bs (actually remove the row)
         offline row incrementality vs live engagement loss   R^2 = 0.8212
         Hájek, π clipped to [0.0001, 0.9999], ≥100 obs / row
live:    content-A incrementality dip → label misattribution on A
ops:     many creator questions now answered offline
```

Needs exploration logging. No $\pi$ $\Rightarrow$ no SNIPS.

## How they know it works (without a new A/B each time)

You **use** SNIPS without a new A/B for every row idea. You do **not** fully **prove** the number without some ground truth. “Works” = leave-one-out SNIPS $\approx$ the engagement you would lose if you **actually** deleted the title/row and the ranker filled the hole.

**1. Identification (math, not a Netflix proof).** If (i) every title you reweight to was shown with $\pi_0>0$ on those contexts, (ii) logged $\pi_0$ is the true $P(\text{show})$, (iii) $m$ really is “what $\pi_e$ would show,” then SNIPS is consistent for $\mathbb{E}[r \mid \pi_e]$. Fails if $\pi$ is a guess, exploration never shows the substitute, or $m$ is wrong.

**2. Simulation (§4.1 — no users).** Known true CTRs. Delete R1, measure true CTR drop. Compare to leave-one-out SNIPS from the Boltzmann logger. The two track; the gap grows with ranker noise. Checks the **estimator**, not Home.

**3. Face validity (content A).** Incrementality of A falls; siblings do not. They found **misattributed labels**, not “A got worse.” The series can catch a bug. It does not show the number equals an A/B lift.

**4. The real proof is still A/Bs they already ran.** 11 historical tests that **removed a Home row**. Offline incrementality vs live engagement loss: $R^2=0.8212$. After that, the next curator question is offline.

If you truly cannot run A/Bs, you cannot prove the counterfactual. Leftovers: sim + audit $\pi$ (does $1/\pi$ look like frequency?) + clip/overlap diagnostics + a natural deletion (title taken down) and see if SNIPS predicted the drop. That last one is an A/B nature ran for you.

## Relation to Our Work
- **Directly useful** for measurement / incrementality, not for ranking. Sibling of Spotify incremental rec: both refuse raw engagement. Spotify asks “show vs hide **this card**, two clocks, do not subtract $\hat{p}_1-\hat{p}_0$.” Netflix asks “delete **this item**, let the ranker substitute, IPS the logged $\pi$.” Different counterfactual. Do not mix the two numbers.
- Plug-in: prevalence / pin-impact dashboards. Report irreplaceability (quality given eligible) separate from universality (how often the system even considers it). Use incrementality time series as a **bug smoke alarm** (their label-misattribution case), not as a launch north star by itself.
- Do **not** import blindly: SNIPS/Hájek need honest $\pi$ and a real exploration module. Match $m$ for leave-one-out is a design choice. $R^2=0.82$ is 11 row tests, not a title-level law. Cascade incrementality is a product of two estimates. Position weights $w_k$ are not identified from the abstract. Short-horizon $r$ can still fight their third principle (long-term value).

## Bottom Line
Raw CTR is the model plus the slot. Incrementality is the hole that remains after substitution — only if you logged the chances.
