# MCGrad: Multicalibration at Web Scale (Best ADS Paper 2026)

## Paper Link

https://arxiv.org/html/2509.19884v1

## Core Idea

MCGrad is a production-scale algorithm for **multicalibrating probabilistic model scores** without requiring engineers to manually define protected groups. It uses recursive LightGBM-style gradient boosting to find miscalibrated regions and correct predicted probabilities safely.

## Problem

Standard calibration asks:

```text
Among examples predicted as 0.8, are roughly 80% actually positive?
```

Multicalibration asks a stronger question:

```text
Is the model calibrated not only globally, but also inside many subgroups?
```

Existing multicalibration methods are hard to use in production because they usually require users to manually define all groups, do not scale well, or hurt metrics like log loss and PRAUC.

## Terminology

| Symbol | Meaning |
|---|---|
| $x$ | Features of one example. |
| $Y \in \{0,1\}$ | Binary label. |
| $f_t(x) \in [0,1]$ | Predicted probability after round $t$. $f_0$ is the base model. |
| $F_t(x)$ | Logit of $f_t$. |
| $h_t$ | GBDT trained at round $t$, with $f_{t-1}(x)$ as an extra feature. |
| $\theta_t$ | Logit rescaling / step size at round $t$. |
| $T$ | Number of boosting rounds kept (0 means “keep the original model”). |

## Method

Start with a base probabilistic predictor $f_0(x) \in [0,1]$. Convert it to logits and repeat:

1. Add the current prediction $f_{t-1}(x)$ as an extra feature.
2. Train a GBDT $h_t(x, f_{t-1}(x))$ on labels $Y$.
3. Update the logit and convert back:

$$
F_t(x) = \theta_t \left(F_{t-1}(x) + h_t(x, f_{t-1}(x))\right),
\qquad
f_t(x) = \mathrm{sigmoid}(F_t(x)).
$$

4. Stop when validation log loss no longer improves.

**Serve time** is the same loop, not one model that eats the whole history. You store $f_0$, the trees $h_1,\ldots,h_T$, and the $\theta_t$. For one $x$:

```text
f ← f_0(x)                         # base model only sees x
for t = 1 .. T:
    h ← h_t(x, f)                  # this tree sees x and the latest f only
    F ← θ_t ( logit(f) + h )
    f ← sigmoid(F)
return f                           # this is f_T
```

You do **not** pass $(x, f_0, f_1, \ldots, f_{t-1})$ into $f_t$. $h_t$ only gets $(x, f_{t-1})$. Older scores are already baked into $f_{t-1}$. If $T=0$, serve $f_0$ and stop.

Same family as gradient boosting (add a correction to the current predictor), **not** the same algorithm:

```text
vanilla GB          each round fits one stump/tree on the residual
                    features = x only
                    start from a constant

MCGrad outer loop   each round fits a whole LightGBM on labels Y
                    extra feature = the latest probability f_{t-1}
                    (not residual, not f_0..f_{t-2})
                    start from a frozen production model f_0
                    then rescale the whole logit: F_t = θ_t (F_{t-1} + h_t)
```

Inside each $h_t$, LightGBM still does ordinary residual boosting. The extra $f_{t-1}$ column is so trees can split on **score bucket × subgroup**, which is the multicalibration group. They re-loop because after you fix groups of $f_0$, the new $f_1$ can be wrong on groups of $f_1$.

The key trick is adding the previous prediction as a feature. This lets the tree find regions like “feature pattern + prediction interval,” which correspond naturally to multicalibration groups.

There is **no separate detect step**. The GBDT is trained to predict $Y$ while it can already see $f$. Globally, $Y-f$ looks like noise. A split is worth making only if some leaf has a **systematic** residual (that slice is over- or under-confident). Those leaves **are** the subgroups. Adding $h$ to the logit then nudges $f$ only in those leaves.

In simplified form, MCGrad tries to drive this close to zero for many tree-defined group functions $h$:

$$
\mathbb{E}\left[h(X, f(X)) \cdot (Y - f(X))\right] \approx 0.
$$

If $h$ is “1 on this leaf, 0 elsewhere,” that equation is just: in this leaf, average $Y$ matches average $f$.

## How a hidden subgroup shows up

Global check can look fine while two slices cancel.

```text
Everyone with f = 0.8     1000 rows    800 positives    80%   looks calibrated

  new users, f ≈ 0.8       200 rows    100 positives    50%   overconfident
  power users, f ≈ 0.8     200 rows    180 positives    90%   underconfident
  everyone else, f ≈ 0.8   600 rows    520 positives    87%
```

You never typed “new users.” The tree sees $(x, f_{t-1})$, including `is_new`, country, and the score. $f_{t-1}=0.8$ alone does **not** say which way to move. Same score, two leaves, opposite $h$:

```text
who              f_{t-1}   mean Y    Y − f      h in that leaf     f_t
new user         0.80      0.50      −0.30      negative (down)    toward 0.50
power user       0.80      0.90      +0.10      positive (up)      toward 0.90
everyone else    0.80      ~0.80      ~0        ≈ 0                stays 0.80
```

Rule: $\mathrm{sign}(h)=\mathrm{sign}(\text{mean }Y-f)$ in the leaf. Overconfident $\Rightarrow$ pull the logit down. Underconfident $\Rightarrow$ push it up. The extra feature $f_{t-1}$ only lets the tree say “this is the 0.8 band **and** a new user,” not “anyone with 0.8 gets lowered.”

Same global 0.8-bucket can stay near 80% positive. The **slices** no longer lie. If the first round cannot find a split that helps validation log loss, $T=0$ and you keep $f_0$.

## Safety / Overfitting Controls

MCGrad emphasizes production safety:

- validation early stopping;
- LightGBM regularization;
- min sum Hessian in leaf;
- logit rescaling;
- default hyperparameters that work without per-model tuning.

Important production behavior:

```text
If the first MCGrad round worsens validation log loss, choose T = 0.
```

So the output remains the original model.

## Results

On 11 benchmark datasets:

- MCGrad reduces multicalibration error on 10/11 datasets;
- average MCE reduction about `56.1%`;
- improves log loss by about `10.4%`;
- improves PRAUC by about `8.1%`.

In Meta production:

- deployed across hundreds of binary classification models;
- on Looper, beat Platt scaling on `24/27` production models;
- PRAUC improved on `24/27` Looper models;
- on another platform, log loss / PRAUC / AUROC / ECE improved for most models.

## Bottom Line

> MCGrad makes multicalibration practical at web scale by automatically discovering miscalibrated regions from features, correcting them with recursive GBDT rounds, and stopping early when calibration would harm predictive performance.
