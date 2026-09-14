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

The key trick is adding the previous prediction as a feature. This lets the tree find regions like “feature pattern + prediction interval,” which correspond naturally to multicalibration groups.

In simplified form, MCGrad tries to drive this close to zero for many tree-defined group functions $h$:

$$
\mathbb{E}\left[h(X, f(X)) \cdot (Y - f(X))\right] \approx 0.
$$

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
