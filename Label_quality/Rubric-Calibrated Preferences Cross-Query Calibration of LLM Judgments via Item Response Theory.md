# Rubric-Calibrated Preferences: Cross-Query Calibration of LLM Judgments via Item Response Theory (Rerank Eval, Cohere)

## Paper Link
https://arxiv.org/abs/2609.35739

## Search-eval logic (read this first)

A **reranker** reorders the top docs for a query. The usual grade is **nDCG** on human **qrels** (sparse, discrete: 0/1/2). When two rerankers are close, nDCG saturates (everyone 1), floors (everyone 0), or ties. On their 14-reranker suite that happens on **45.6%** of NanoBEIR queries.

An LLM judge can compare docs **inside one query** (A beats B beats C) with fine grain. Those scores have **no shared unit across queries**: “+2” on `best espresso machine` is not “+2” on `why is the sky blue`. Absolute grades (relevant / not) share a scale but tie almost everyone.

**RCP:** keep the within-query order from a listwise tournament. Use a **fixed yes/no rubric** as the shared exam questions. **IRT** (the same model that scores students on a common test) puts every query’s tournament scores on **one** scale. Then nDCG uses a **continuous** gain instead of a 0/1/2 qrel. Label the candidate pool **once**; any later reranker is scored with no new judge calls.

## One-Line Summary
Pairwise LLM prefs set order inside a query; a shared rubric + IRT puts those scores on one scale so nDCG can tell close rerankers apart.

## Core Problem
Human qrels are too coarse and sparse for today’s rerankers. Relative LLM judgments cannot be averaged across queries. Absolute LLM grades cannot split near-ties. Need both: fine order **and** a number that means the same on every query.

## Terminology

| Symbol | Plain meaning |
|---|---|
| qrel | Human graded relevance for (query, doc). Sparse, discrete. |
| $q_j$, $d_i$ | Query $j$; candidate doc $i$. |
| Stage A / $\hat{\theta}_i^{\mathrm{BT}}$ | Listwise LLM tournament $\to$ Bradley–Terry score. Order **inside** $q_j$ only. |
| C1–C5 | Shared yes/no rubric (topical $\to$ thorough). Same questions on every query. |
| $Y_{ic}=1$ | Doc $i$ passes criterion $c$. |
| $\beta_c$, $\gamma_c$ | Criterion difficulty / how steeply pass-rate rises. Shared across queries. |
| $\tau_j$, $\alpha_j$ | Stretch and shift that put query $j$’s BT scores onto the shared scale. |
| $\tilde{\theta}_{ij}$ | Calibrated ability: $\tau_j \hat{\theta}_i^{\mathrm{BT}} + \alpha_j$. |
| $g(\tilde{\theta})$ | Continuous gain in $[0,1]$ for RCP-nDCG. |
| Count-nDCG | Baseline: gain = fraction of rubric boxes ticked (ties if same count). |

## Method

```text
Stage A   windows of 10 docs → LLM listwise scores → BT prefs → θ̂_BT
          (order inside this query; scale is arbitrary)
Stage B   same judge, yes/no on C1–C5 per doc
IRT merge stretch/shift each query so “pass C4 at 50%” means the same ability
gain g    weighted pass-probabilities → plug into nDCG
freeze    label the pool once; score any reranker offline
```

Bradley–Terry (Stage A): $P(i \succ i') = \sigma(\theta_i - \theta_{i'})$.

2PL IRT (merge). Documents are students; criteria are exam items:

$$
P(Y_{ijc}=1) = \sigma\left( \gamma_c \left( \tau_j \hat{\theta}_i^{\mathrm{BT}} + \alpha_j - \beta_c \right) \right)
$$

$$
\tilde{\theta}_{ij} = \tau_j \hat{\theta}_i^{\mathrm{BT}} + \alpha_j
$$

Order inside a query is **unchanged** (affine of BT). Cross-query: $\tilde{\theta}=\beta_c$ means “50% chance to pass $c$” on **every** query.

Gain (discrimination-weighted pass probs):

$$
g(\tilde{\theta}) = \frac{\sum_c \gamma_c \sigma\left( \gamma_c (\tilde{\theta} - \beta_c) \right)}{\sum_c \gamma_c}
$$

Shipped rubric (NanoBEIR / Qwen3.5-397B), easy $\to$ hard: topical, useful, entity match, **direct answer**, thorough. Ablation: reranker-pair winners flip only if the rubric ignores the query or all criteria sit at one end of the scale.

## Concrete Example
Query A: `best espresso machine`. Docs almost all topical (C1). Tournament: $d_1 \succ d_2$ by a hair. Raw BT $= +0.3$ vs $+0.1$ — meaningless next to Query B.

Query B: `why is the sky blue`. Only the Wikipedia hit passes C4 (direct answer). Its raw BT $= +0.3$ too.

Without IRT you would average those $+0.3$s. With IRT, Query A’s $\tau_j$ is small (everyone passes C1, nobody is a C4), so $+0.3$ stays a **small** $g$. Query B’s Wikipedia hit sits near $\beta_{\mathrm{C4}}$ and gets $g$ near the “direct answer” step. Same raw BT, different **calibrated** gain.

Ask analog: two pins both “must-refuse = yes” is Count-nDCG (same tick count). RCP would keep A4’s pairwise order **and** put “refuses a jailbreak” and “refuses a mild ask” on one exam scale. Do not treat raw judge logits as comparable across prompts.

## Results

```text
qrel nDCG fails (sat/floor/tie)   45.6% NanoBEIR, 30.7% BRIGHT queries
paired t-test separates rerankers  34.1% (qrel-nDCG) → 63.5% (RCP-nDCG)  NanoBEIR
human 46 annotators, 311 contests  RCP gain AUC 0.910 vs qrel 0.651
                                   where exactly one metric matches humans:
                                   RCP-nDCG 72.4% of 185 contests
TREC-DL / NIST                     RCP-nDCG agrees on every pair NIST separates
2PL vs raw BT for pass probs       ECE 0.017 vs 0.371
```

Released: code, LLM judgments, 7,080 human grades. Pool labeled once.

## Relation to Our Work
- **Directly useful** for LLM-as-judge / label quality. Sibling of Spotify QRI: both fix search judges. QRI pastes **debiased historical clicks** so the judge shares *user* intent. RCP does not use clicks; it **calibrates** relative LLM prefs onto a shared rubric scale so scores can be pooled. Complementary, not a substitute: QRI for “what did users mean?”; RCP for “can I compare two queries’ judge numbers?”
- Plug-in: Eval Hub / PINSAFE. Stage A = pairwise or listwise A4 on the same journey. Stage B = a **fixed** must-refuse / utility rubric (not a new rubric per item). IRT merge before you average prevalence or pick a policy in `training.py`. Freeze the labeled pool like they freeze candidate qrels — do not let the editor rewrite $g$ mid-loop.
- `training.py` compare: same evaluate $\to$ gate family, **different artifact**. They produce a **calibrated label**. SkillOpt / `training.py` edit a **policy**. Use RCP (or Count-nDCG) as the **score the gate reads**, not as the editor. Count-nDCG is the naive “sum rubric ticks” they beat.
- Do **not** import blindly: rubric is retrieval-shaped (C1–C5); Ask needs its own monotone criteria. IRT needs enough docs that pass **and** fail each $c$. Judge cost is paid **up front** on the pool (they use a huge Qwen). ECE is vs the **same** judge’s ticks, not vs humans. 14 rerankers / NanoBEIR is not PINSAFE. Affine map preserves Stage-A mistakes: a biased tournament stays biased, just on one scale.

## Bottom Line
Relative LLM prefs are a ranking. A shared rubric is the exam. IRT is the curve that lets you treat “+2” on two queries as the same unit — then nDCG stops tying.
