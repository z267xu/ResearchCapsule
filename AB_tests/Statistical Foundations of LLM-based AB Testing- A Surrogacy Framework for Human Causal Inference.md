# Statistical Foundations of LLM-based A/B Testing: A Surrogacy Framework for Human Causal Inference
---

## Paper Link

https://arxiv.org/abs/2606.17165

## Paper Summary

### The problem
As LLMs are increasingly used as stand-ins for human participants in experiments (to save cost/time), the paper asks: **when does a treatment effect estimated on LLM-generated outcomes actually recover the true treatment effect for humans?**

Perfect distributional equivalence between LLM outputs and human outcomes would guarantee this, but that's unrealistic in practice.

### The framework: surrogacy
The authors adapt classical **surrogate endpoint theory** (from clinical trials, where a short-term biomarker stands in for a long-term outcome) to LLM-generated outcomes. Two key assumptions:

1. **Surrogacy** — conditional on the LLM output ($Y^*$) and covariates, treatment has no *residual* direct effect on the true human outcome ($Y^*$ fully mediates the treatment effect).
2. **Comparability** — the relationship between $Y^*$ and human outcome $Y$ (the "calibration function" $\mu$) is stable across the human sample and the artificial LLM sample.

Under these two assumptions, they prove the human ATE (average treatment effect) can be identified by:
- learning a calibration function $\mu(X, Y^*)$ that maps LLM outputs to human outcomes, using a human sample,
- applying that function to LLM-generated data to estimate the ATE — without needing more real human data.

This is weaker than requiring the LLM to replicate human responses exactly; the LLM just needs to carry the *right information*, not be on the same scale/distribution.

### Role of LLM stochasticity
Because LLM outputs are noisy, using a **single draw per unit** can:
- violate surrogacy,
- bias the calibrated estimate toward zero (attenuation — a classical errors-in-variables effect),
- inflate variance.

**Fix:** average over K independent LLM draws per unit. As K grows, bias and variance shrink and surrogacy is restored — at the cost of more LLM calls.

### Diagnostic tools
- **Falsification test** for surrogacy, using historical human data (can reject surrogacy, but passing it doesn't guarantee validity for a genuinely novel treatment).
- **Sensitivity bound** on worst-case bias from limited distributional overlap between the human and LLM samples (based on total variation distance).

### Empirical validation (Upworthy headlines dataset)
Testing "headline phrased as a question" vs. not, using 417 real A/B tests:
- **Raw LLM (gpt-4o-mini) predictions recovered only ~39% of the true human treatment effect.**
- **Nonparametric calibration** (random forest / gradient boosting) closed this gap to within sampling error; **linear calibration remained significantly attenuated.**

### Core takeaway
> **A/B testing on LLM responses is correct only by assumption, whereas A/B testing on humans is correct by design.**

Assumptions can be partially checked against historical data but **never fully verified for a genuinely novel treatment** — meaning the approach is least trustworthy exactly where it would be most valuable. LLM-based outcomes should be treated as **complementary to, not a substitute for**, real experiments.

---

## 2. Worked Synthetic Example

To build intuition, here's a toy numeric example mirroring the paper's method.

**Setup:** Testing "headline with question mark" (W=1) vs. "no question mark" (W=0) on click-through rate (CTR).

### Step 1 — Human pilot sample (both Y and $Y^*$ observed)

| Unit | W | Y (real CTR) | $Y^*$ (LLM guess) |
|---|---|---|---|
| A | 0 | 4.9 | 19.8 |
| B | 0 | 5.2 | 20.2 |
| C | 0 | 5.0 | 20.0 |
| D | 1 | 7.8 | 20.9 |
| E | 1 | 8.3 | 21.2 |
| F | 1 | 8.0 | 21.0 |

- **True human ATE:** 8.03 − 5.03 = **3.0**
- **Raw LLM ATE:** 21.03 − 20.0 = **1.0** --> badly *attenuated* (LLM signal barely moves with treatment)

### Step 2 — Fit calibration function $\mu(Y^*$) on pilot data (OLS)

$\mu(Y^*) \approx −50.3 + 2.77Y^*$

### Step 3 — Apply $\mu$ to a large LLM-only sample (no real humans needed)

| Unit | W | $Y^*$ (LLM guess) | $\mu(Y^*$) calibrated prediction |
|---|---|---|---|
| G | 0 | 19.9 | 4.83 |
| H | 0 | 20.1 | 5.38 |
| I | 0 | 20.0 | 5.10 |
| J | 1 | 21.1 | 8.15 |
| K | 1 | 20.8 | 7.32 |
| L | 1 | 21.0 | 7.87 |

- **Raw LLM ATE on new sample:** 20.97 − 20.0 = **0.97** (still badly attenuated)
- **Calibrated ATE:** 7.78 − 5.10 = **2.68**

### Result

| Estimator | Value | % of true effect |
|---|---|---|
| True human ATE | 3.00 | 100% |
| Raw LLM ATE | 0.97 | 32% |
| **Calibrated LLM ATE** | **2.68** | **89%** |

**Takeaway:** raw LLM predictions can't be trusted directly (wrong scale, attenuated signal), but a small human pilot used to fit a calibration function lets you run the bulk of the "experiment" cheaply via the LLM while recovering most of the true effect — *provided* the calibration transfers correctly to the new items being tested (the comparability assumption).

---

## 3. How to obtain the calibration function in practice

Two options, matching how such a pilot could realistically be run:

### Option A — Concurrent human pilot (e.g., 3–5 day pilot)
Run a small real experiment alongside the LLM-based test: expose a subset of real users, measure real Y, also generate $Y^*$ from the LLM for the same units, fit $\mu$ on this pilot, then apply $\mu$ to a much larger LLM-only sample.

- Directly addressed in the paper's **Section 6.5 (Pilot allocation)** — framed as a cost tradeoff (pilot cost vs. cost of a wrong deployment decision), with a formula for optimal pilot size.

### Option B — Historical / similar past experiments
If historical A/B tests exist where both real human outcomes and LLM-generated predictions (retroactively computed) are available, fit $\mu$ on that historical data — no new pilot needed. This is exactly what the paper does with the **Upworthy dataset**.

- Catch: $\mu$ learned on historical data only transfers if the **new** treatment is similar enough to what's in the historical data (comparability assumption). The paper's falsification test and sensitivity bound partially guard against this, but **cannot fully verify validity for a genuinely novel treatment**.

**Practical recommendation:** use historical data for calibration when possible (cheap), but pair it with a small concurrent pilot as a sanity/positive-control check — and consider blending the pilot estimate with the calibrated LLM estimate for extra precision.

---

## 4. Open Concern: Novelty Effects Contaminating a Short Pilot

### The concern
If the feature being tested is **novel**, a short pilot (e.g., 3–5 days) can itself suffer from a **novelty/curiosity effect** — users react unusually strongly at first, before settling into steady-state behavior. If the calibration function is trained on this novelty-inflated pilot, it will **exaggerate** the ATE when scaled up via the LLM.

### Why this is a different failure mode than what the paper addresses
1. **The paper's problem:** does the LLM's guess ($Y^*$) correctly track the human outcome (Y), *given that Y is measured correctly*? --> surrogacy / comparability.
2. **This concern:** is the human outcome (Y) *itself* measured correctly during a short pilot? --> classic novelty/primacy bias, independent of LLMs entirely.

The paper's diagnostics (falsification test, sensitivity bound) check whether $Y^*$ <--> Y is stable — they have **no mechanism to detect that Y itself is a distorted proxy** for the long-run outcome of interest. A calibration function fit on a novelty-inflated pilot will be judged "valid" by these diagnostics while still producing an exaggerated ATE at scale.

### Numeric illustration

Suppose the true steady-state effect is only **1.0**, but a 3-day pilot shows a novelty-inflated effect of **3.0**:

| Unit | W | Y (novelty-inflated) | $Y^*$ (LLM guess) |
|---|---|---|---|
| A | 0 | 5.0 | 20.0 |
| B | 0 | 5.0 | 20.0 |
| C | 0 | 5.0 | 20.0 |
| D | 1 | 8.0 | 21.0 |
| E | 1 | 8.0 | 21.0 |
| F | 1 | 8.0 | 21.0 |

Observed pilot ATE = 3.0 (vs. true steady-state ATE of 1.0).

Fitting $\mu$ on this data and applying it to the large LLM sample reproduces roughly the same inflated **calibrated ATE (~2.68)** as before — the calibration function faithfully launders the novelty spike into every future prediction, at scale, with no self-correcting mechanism. You'd deploy believing the true effect is ~2.7 when it's actually closer to 1.0.

### How this maps onto the paper's own concepts
- Resembles the paper's **Section 4.2 surrogacy-violation scenario** (Figure 4a): treatment has a direct effect on Y that isn't mediated by whatever stable signal $Y^*$ captures — here, "novelty decay" is a time-dependent direct effect.
- Connects to **Section 6.4 (long-term outcomes)**: calibrating on a short-term pilot when the target is a steady-state/long-term effect requires a **two-step surrogate chain** ($Y^*$ --> $Y_{short}$ --> $Y_{long}$), and novelty effects break the second link.

### Mitigations

| Approach | What it does |
|---|---|
| Extend the pilot window | Let novelty decay before fitting $\mu$ — directly fixes the root cause, at higher cost |
| Split pilot into early/late windows | Fit $\mu$ separately on early vs. later days; a shifting calibration coefficient is a red flag (an application of the paper's temporal-split diagnostic, repurposed to detect novelty rather than distribution shift) |
| Treat short-term pilot Y as itself a surrogate for long-term Y | Stack two surrogate problems (à la Athey et al.'s surrogate index, cited in the paper), each with its own comparability check |
| Weight pilot size/duration by novelty risk | Extend the paper's Section 6.5 pilot-sizing formula to explicitly account for expected novelty decay, not just statistical power |
| Positive/negative control checks | Track the treatment effect trajectory across pilot days; a declining trend signals the pilot hasn't reached steady state |

### Bottom line
A short pilot risks baking in a novelty-inflated human outcome, and the calibration step will faithfully (and invisibly) launder that inflation into the large-scale LLM-based ATE. The paper's surrogacy diagnostics check whether the **LLM** is trustworthy — not whether the **pilot itself** is measuring the right thing. That risk has to be managed separately, through pilot design (duration, timing, decay monitoring).

---
