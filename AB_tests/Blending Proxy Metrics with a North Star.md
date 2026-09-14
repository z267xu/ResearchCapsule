# Blending Proxy Metrics with a North Star (Experimentation, Netflix)

## Paper Link
https://arxiv.org/abs/2606.21745

## One-Line Summary
When you observe both a sensitive proxy and a noisy contemporaneous north star, launch on a sample-size-dependent blend of their estimated treatment effects — not on either metric alone.

## Core Problem
Classic surrogate papers assume the north star is **unobserved** (long-run retention, months out). Netflix’s everyday problem is different: they **do** observe the north star (e.g. plays, end-of-test retention), but everyday A/Bs are underpowered for it. Teams then face three ugly questions:

1. In a huge test that *is* powered for the north star, should you still listen to the proxy?
2. What if proxy and north star disagree?
3. If the proxy is excellent, should the program run smaller/more tests or larger/fewer?

Choosing proxy-only or north-star-only is a false binary.

## Terminology

Read this table before the equations. Every symbol below is an **experiment-level** object unless noted.

| Symbol | Meaning |
|---|---|
| $P$ | True treatment effect on the **proxy** (clicks at Netflix; surrogate prevalence for us). May be a vector. |
| $Y$ | True treatment effect on the **north star** (plays / retention at Netflix; LLM / PPS prevalence for us). The quantity whose launches we care about. |
| $X = (P, Y)$ | Stacked true effects for one experiment. **Not observed.** Chou treats $X$ as drawn i.i.d. across experiments, Gaussian, mean zero. |
| $\hat{X} = (\hat{P}, \hat{Y})$ | Estimated ATEs from the current experiment (difference in means). **Observed.** |
| $n$ | Per-arm sample size in the paper (users / impressions). In our toy it is a **relative LLM-label budget**. |
| $\Omega$ | **Unit-level** sampling covariance of the raw metrics (how noisy one user’s proxy and north-star outcomes are). Bigger $\Omega$ $\Rightarrow$ noisier ATEs. |
| $2\Omega/n$ | Sampling covariance of $\hat{X}$. The $2$ is treatment + control; $n$ in the denominator is why bigger tests shrink estimation error. |
| $\Sigma_X$ | Covariance of **true** $X$ **across experiments** (signal: how much $P$ and $Y$ really move together from test to test). |
| $\Sigma_{\hat{X}} = \Sigma_X + 2\Omega/n$ | Total covariance of the **observed** estimates = cross-experiment signal + within-experiment noise. |
| $\Gamma = \mathrm{Cov}(X, Y)$ | Last column of $\Sigma_X$: how each component of $X$ co-moves with the north star. $\Gamma_P = \mathrm{Cov}(P,Y)$, $\Gamma_Y = \mathrm{Var}(Y)$. |
| $A = (a,\,1-a)$ | Blend weights, nonnegative and summing to 1. $a$ = weight on the proxy. |
| $\hat{Z}(A)$ | Blended launch statistic $A^\top \hat{X}$. |
| $z$ | Critical value for “significantly $> 0$” (e.g. $z = 1.645$ for one-sided $\alpha = 0.05$). |
| $R(A)$ | **Expected north-star return** of the rule “launch iff $\hat{Z}(A)$ is significant”: $\mathbb{E}[Y \cdot \mathbf{1}\{\text{launch}\}]$. Not an estimate of $Y$. |
| $\tilde{A}$ | Closed-form approximation to the $A$ that maximizes $R(A)$. |
| $\tau_Y$ | A target north-star effect used only in their informal “power” calculation. |
| $\rho$ | Cross-experiment correlation of true $(P,Y)$. |

Mnemonic: $\Sigma_X$ is **how experiments differ**; $\Omega$ is **how noisy one experiment’s users are**.

## Method

Each experiment has unobserved true effects $X = (P, Y)$ drawn from $\Sigma_X$. You observe noisy $\hat{X}$ with

$$
\hat{X} \mid X \sim \mathcal{N}(X, 2\Omega/n).
$$

Launch if the blended statistic is significantly positive:

$$
\hat{Z}(A) = a\,\hat{P} + (1-a)\,\hat{Y},
\qquad
\text{launch iff }
\hat{Z}(A) > z\sqrt{A^\top (2\Omega/n)\,A}.
$$

$A$ is chosen to maximize expected north-star return of that rule, not to estimate $Y$ itself:

$$
R(A) = \mathbb{E}\left[Y \,\mathbf{1}\{\hat{Z}(A) > z\,\mathrm{se}(\hat{Z})\}\right].
$$

Closed-form approximation (accurate for large enough $n$):

$$
\tilde{A} \propto \left(\Sigma_X + (1+z^2)\,2\Omega/n\right)^{-1}\Gamma.
$$

Read this as a **penalized regression of $Y$ on $X = (P,Y)$**. The penalty $(1+z^2)\,2\Omega/n$ is measurement error: it shrinks weight toward whichever metric is precise *within* an experiment relative to how much it varies *across* experiments.

Consequences:

- $n \to \infty$ $\Rightarrow$ $a \to 0$ (trust the north star).
- Better proxy (larger $\Gamma_P$, smaller $\Omega_P$) $\Rightarrow$ larger $a$ at any fixed $n$.
- Stricter $z$ (harder to launch) $\Rightarrow$ more weight on precise proxies.

Estimate $\Sigma_X$ and $\Omega$ from past experiments (nonparametric / empirical Bayes / hierarchical), plug in, drop any negative weights, renormalize onto the simplex. If $n$ is below their bound $\underline{n}$, solve $R(A)$ numerically instead of using $\tilde{A}$.

**Program-level implication.** Average return per allocated user $R^*(n)/n$ decreases in $n$ for typical launch thresholds ($z \le 1+\sqrt{2} \approx 2.41$, one-sided $\alpha \gtrsim 0.008$). Extra traffic should open a **new** test, not fatten existing ones. Combined with blending: a **better proxy $\Rightarrow$ smaller and more experiments**; a worse proxy $\Rightarrow$ larger and fewer.

They also write an informal “power” sample size: probability that $\hat{Z}$ is significant when the true north-star effect is $\tau_Y$. Extra inflation $I(\theta)$ grows as proxy–north-star alignment gets worse; if residual noise is too large relative to the conditional mean, no finite $n$ hits 80%.

## Concrete Example (our metrics, their algorithm)

Map our two prevalence estimators onto Chou’s $(P, Y)$:

```text
P  surrogate prevalence ATE     (score-bucket calibration; almost every experiment)
Y  LLM / PPS prevalence ATE     (direct labels; only a few experiments)
```

Both are experiment-level deltas in **percentage points** of the same harm (e.g. adult-content prevalence). Chou’s launch blend needs **both** $\hat{P}$ and $\hat{Y}$ on the *current* test. The few LLM-labeled tests are how you estimate $\Sigma_X$. Everyday surrogate-only tests cannot form $\hat{Z}(A)$ — they stay proxy-only ($a = 1$). That is a real gap vs Netflix, where plays exist on every experiment and are just noisy.

### Step 1 — Learn $\Sigma_X$ from the few paired tests

Six past A/Bs that paid for LLM labels (already demeaned in the covariance; Chou assumes mean-zero effects):

```text
exp   P̂ surrogate   Ŷ LLM
1        +1.20       +0.90
2        +0.80       +0.50
3        +0.40       +0.35
4        -0.20       -0.05
5        +0.10       -0.10    ← mild disagreement
6        +1.50       +1.10
```

Sample covariance (pp²) and $\Gamma = \mathrm{Cov}(X,Y)$ = last column:

$$
\Sigma_X =\begin{bmatrix} 0.427 & 0.312 \\ 0.312 & 0.238 \end{bmatrix},
\qquad
\Gamma = (0.312, 0.238),
\qquad
\rho \approx 0.98.
$$

Historically the surrogate and the LLM delta move together. That is what will keep $a$ large until $\hat{Y}$ is very precise.

### Step 2 — Measurement error $2\Omega/n$

$n$ here is a **relative labeling / traffic budget** ($n = 1$ = a typical rare LLM measurement). Surrogate SEs stay small because they use the full log; LLM SEs shrink only if we buy more labels.

At $n = 1$: $\mathrm{se}(\hat{P}) = 0.08$ pp, $\mathrm{se}(\hat{Y}) = 0.35$ pp, and

$$
V(n) = \frac{2\Omega}{n} = \frac{1}{n}
\begin{bmatrix} 0.0064 & 0.005 \\ 0.005 & 0.1225 \end{bmatrix}.
$$

One-sided launch threshold $z = 1.645$ ($\alpha = 0.05$), so the Chou penalty factor is $1+z^2 \approx 3.71$.

### Step 3 — Plug into their closed form

$$
\tilde{A} \propto \left(\Sigma_X + (1+z^2)\,V(n)\right)^{-1}\Gamma,
$$

then drop negative weights and renormalize onto the simplex.

At $n = 1$:

$$
M = \Sigma_X + 3.71\,V
\approx\begin{bmatrix} 0.450 & 0.331 \\ 0.331 & 0.692 \end{bmatrix},
\qquad
\tilde{A} \propto M^{-1}\Gamma \approx (0.678, 0.020),
$$

so $A = (0.971, 0.029)$ — **97% surrogate, 3% LLM**.

As we buy more LLM labels, weight moves toward `Y` (same law as their clicks → plays schedule):

```text
n     se(Ŷ)    a (surrogate)   1-a (LLM)
1     0.35        0.97           0.03
4     0.18        0.89           0.11
16    0.09        0.67           0.33
64    0.04        0.34           0.66
256   0.02        0.11           0.89
```

### Step 4 — A new test that has both (the rare case)

Treatment vs control:

```text
P̂ = +0.70 pp   (surrogate: harm went up)
Ŷ = +0.05 pp   (LLM: basically flat)
```

$$
\hat{Z}(A) = a\hat{P} + (1-a)\hat{Y},
\qquad
\text{launch iff } \hat{Z}/\mathrm{se}(\hat{Z}) > 1.645.
$$

| $n$ | $a$ | $\hat{Z}$ | $z$-stat | vs proxy-only | vs LLM-only |
|---|---|---|---|---|---|
| 1 | 0.97 | 0.68 | 8.5 launch | launch (8.8) | no-launch (0.14) |
| 16 | 0.67 | 0.49 | 14 launch | launch | no-launch (0.57) |
| 256 | 0.11 | 0.12 | 6.3 launch | launch | still weak |

At everyday LLM budgets, the blend **follows the surrogate**. LLM-only would kill the launch; proxy-only would ship. Chou does not pick either — but with $\rho \approx 0.98$ and a noisy $\hat{Y}$, a “LLM flat” does **not** veto a surrogate win until $\hat{Y}$ is almost as precise as $\hat{P}$. That is the algorithm working as designed, not a bug: it treats $\hat{Y} = 0.05$ as measurement error around a historically tight $P$–$Y$ line.

Netflix’s published schedule (same math, different metrics):

```text
n ≲ 2M / arm     →  100% clicks
n ≈ 5M / arm     →   52% clicks, 48% plays
n  = 25M / arm   →  ~10% clicks, ~90% plays
```

### Step 5 — A new test that has only the surrogate (the common case)

```text
P̂ = +0.70 pp
Ŷ = missing
```

You cannot compute $\hat{Z}(A)$. Honest options:

```text
1. a = 1: launch on surrogate + your usual sign test / CI   (not Chou)
2. run LLM labels on this test, then go to Step 4
3. do not invent Ŷ from P̂ and call it a north star
   (that is a surrogate index / our KDD map, a different estimator)
```

The paired history still earns you something: it tells you whether $a$ *would* have been $\approx 1$ anyway. If $\rho$ is high and typical $n$ is 1, Chou is saying “your everyday surrogate-only launches are close to optimal.” If $\rho$ were 0.4, the same math would say “stop launching on surrogate alone; buy LLM labels or run bigger paired tests.”

What this is **not**: the KDD bucket-calibration system itself. Chou blends two already-computed experiment ATEs for a **launch weight**. He does not produce the prevalence number.

## Results
**Simulations.** Blend beats proxy-only and north-star-only on cumulative north-star return at every `n`. Proxy-only false-positive rate is **above** 5% and can **rise** with `n` unless `ρ = 1` (larger tests make a misaligned proxy more confidently wrong). Blend’s false-positive rate interpolates and falls toward the north star’s 5% as `n` grows. Qualitative picture survives heavy-tailed (`t_3`) effects.

**Netflix program.** 15 A/B tests, 50 arms. Clicks SE-ratio ~12, ~60% of arms significant; plays SE-ratio ~2, ~25% significant. Cross-fold OLS of plays on clicks matches raw OLS (relationship is not just correlated measurement error). Blend dominates both single-metric rules across observed sizes `n ∈ [1M, 25M]`. Even at 25M, clicks-only still beats plays-only on expected return — plays stay noisy — but adding plays still helps vs clicks-only.

## Relation to Our Work
- **Directly useful** for the measurement / prevalence track;
- Plug-in: treat **surrogate prevalence as $P$** (always on) and **direct LLM prevalence as $Y$** (rare). Estimate $\Sigma_X$ from the paired tests, then blend only when a test paid for LLM labels. Do not pick one metric by habit.
- This is the contemporaneous-north-star cousin of the IV long-run surrogate note already in the capsule. They cite Athey/Chetty/Imbens, Tripuraneni “choosing a proxy from past experiments,” and Netflix’s own surrogate-index eval. The distinctive claim is: the north star is observed-but-weak, so the decision rule should **move toward it as power grows**.
- Different object than our KDD paper. We amortize LLM labels through score buckets to estimate impression-weighted prevalence. Chou blends two experiment-level ATEs for a launch decision. Compatible: use our surrogate as `P`, a sparse human audit or a business north star as `Y`, then blend.
- Do **not** import blindly: Gaussian zero-mean effects, IID experiments, launch-if-significant as the only decision rule, and return defined as $\mathbb{E}[Y \cdot \mathbf{1}\{\text{launch}\}]$. A badly biased LLM proxy that is stably correlated with humans in the past can still get a large $a$ in small tests. Negative or wrongly signed proxies are dropped, not modeled.
- Open question: should day-level sign tests on surrogate deltas be replaced by, or blended with, a slower human-audit north star using this $A(n)$ schedule?

## Bottom Line
A good proxy earns weight when the test is small; the north star earns it back as the test gets large. The program should run more, smaller tests when the proxy is strong — and never treat “proxy vs north star” as an either/or.
