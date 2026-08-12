# Case Study: Learning Robust, Long-run Surrogate Metrics with Modeling and Instrumental Variables

## Paper Link

https://dl.acm.org/doi/epdf/10.1145/3770854.3783922

## Core Idea

The paper proposes a way to build **fast surrogate metrics for long-run A/B test outcomes** by training user-level machine learning models with an instrumental-variable-inspired correction, using randomized experiment assignments as instruments.

## Problem

Teams often care about long-run outcomes that take weeks or months to observe. Waiting slows iteration. Surrogate metrics should move faster while still predicting the long-run target.

Simple surrogates can be unreliable because:

- they may only correlate with the long-run outcome, not causally mediate it;
- hidden confounders may affect both short-run behavior and long-run outcomes;
- historical A/B-test meta-analysis may use stale data;
- linear models may miss nonlinear relationships.

## Method

Train user-level surrogate models that predict long-run business outcomes from short-run engagement features:

```text
BV1: binary long-run business value metric
BV2: count/regression long-run business value metric
```

Variables:

```text
Y  = long-run outcome
X  = short-run engagement features
W  = known confounders
Z  = randomized A/B test assignments
```

Two-stage IV-inspired training:

```text
Stage 1:
X_hat = h(Z, W)

Stage 2:
Y_hat = g(X_hat, W)
```

### Clarified Stage Roles

| Stage | Inputs | Labels / target | Notes |
|---|---|---|---|
| Stage 1 | `Z`, `W` | raw `X` | learns to reconstruct engagement from instruments |
| Stage 2 | `X_hat`, `W` | `Y` | learns long-run prediction from debiased engagement |
| Daily inference | latest raw `X`, `W` | — | reuse fixed Stage-2 model on latest engagement |

Important distinction:

- In Stage 1, raw `X` is the **label**, not the input.
- In Stage 2, the model uses `X_hat` and `W`, not raw `X`.
- Directly training `Y ~ X, W` can be biased by hidden confounders; Stage 1 replaces `X` with the part of engagement explained by randomized experiments.

## Concrete Example

For one user:

```text
X = {
  likes_last_3_days: 12,
  sessions_last_3_days: 5,
  time_spent_min: 40
}

W = {
  country: JP,
  tenure_days: 180,
  device: iOS
}

Z = {
  test_A_treatment: 1,
  test_B_treatment: 0,
  test_C_control: 1
}

Y = 1   # still highly engaged 2 weeks later
```

Stage 1 predicts debiased engagement:

```text
X_hat = h(Z, W)
# e.g. likes=10.2, sessions=4.7, time_spent=36.5
```

Stage 2 predicts long-run outcome:

```text
Y_hat = g(X_hat, W)
# e.g. P(BV1=1) = 0.71
```

In a new A/B test, aggregate daily surrogate scores by arm:

```text
Control:   mean BV1_hat = 0.42
Treatment: mean BV1_hat = 0.45
Surrogate lift: +0.03
```

## Results

User-level prediction:

```text
BV1 AUC:
GBT surrogate: 0.94
NN surrogate:  0.93
Baseline:      0.79

BV2 RMSE:
GBT surrogate: 3.90
NN surrogate:  4.01
Baseline:      4.45
```

A/B-test-level prediction:

```text
Pearson correlation with long-run outcome > 0.9
BV2 magnitude slope ≈ 1.02
```

Post-launch consistency:

```text
If both surrogate and target metric are s.s. positive pre-launch,
odds of consistent post-launch effect are much higher (OR=32).
```

Bayesian Optimization:

```text
Optimizing ranking/value-model parameters for the surrogate
drove actual long-run BV2 improvements in multiple tuning sequences.
```

## Discussion Summary

Our discussion clarified several points about the IV surrogate method.

### 1. Stage roles for `X` and `W`

1. **Stage 1 and Stage 2 both use `W`.**  
   Stage 1 uses `Z` and `W` to predict `X`. Stage 2 uses `X_hat` and `W` to predict `Y`.

2. **Raw `X` is not an input in Stage 1.**  
   Observed short-run engagement is the Stage-1 target. The Stage-1 model learns how randomized experiment assignment and known confounders explain engagement.

3. **Why not skip Stage 1?**  
   Training `Y ~ X, W` directly can pick up confounding patterns such as “high-quality users engage more today and stay longer later.” The IV-inspired Stage 1 focuses Stage 2 on engagement variation linked to randomized treatments, making the surrogate more robust for predicting long-run treatment effects.

### 2. Where does `Y` come from if long-run outcome is unknown?

`Y` is not unknown forever. It is unknown when we want a fast A/B decision. For model fitting, we use older cohorts for whom the long-run outcome has already arrived.

| Phase | Do we observe `Y`? | What we do |
|---|---|---|
| Training | Yes | Wait until the long-run window ends, then use historical users |
| Inference / A/B tests | No | Predict `Y_hat` from recent short-run features |

Example timeline:

```text
Training data from an earlier window:
  Day 1–3:   observe short-run engagement X
  Day 1–3:   observe experiment assignment Z and confounders W
  Day 17:    observe long-run outcome Y  (already happened)

Serving on a new A/B test later:
  Day 30–32: observe current short-run engagement X_new and W_new
  Day 32:    compute Y_hat = g(X_new, W_new)
  Day 46:    true Y would appear, but we do not wait
```

So the structural model:

```text
Y = g(X_explained_by_randomized_experiments, W) + error
```

is the **training objective**, not what we observe at decision time.

- In training: `Y` is the already-realized long-run label.
- In production: we only compute `Y_hat`, because the long-run effect has not happened yet.

### 3. How to apply the algorithm to a new experiment

For a new experiment, true long-run `Y` is unknown. That does not break the method. The method only needs historical `Y` for training, not for the new experiment.

What must already exist:

```text
Past users:
  short-run X
  confounders W
  old A/B assignments Z_old
  realized long-run Y

Train:
  Stage 1: X_hat = h(Z_old, W)
  Stage 2: Y_hat = g(X_hat, W)
```

How to apply it to a new experiment that aims to improve long-term retention:

```text
1. Launch the new A/B test for a short window, e.g. 3–7 days.
2. Collect short-run engagement X_new and confounders W.
3. Score the fixed Stage-2 model: Y_hat = g(X_new, W).
4. Compare arms: mean(Y_hat | treatment) vs mean(Y_hat | control).
5. Use that as the fast estimate of long-run retention lift.
```

The algorithm answers:

```text
Given how treatment changed short-run behavior,
what long-run retention change do we expect?
```

not:

```text
Do we already know the long-run Y for this experiment?
```

Before launch, we may know little about whether the new change affects long-run retention. That is normal. The method does not require that prior knowledge. It only assumes something weaker:

```text
If the new treatment affects long-run retention,
it likely does so through short-run engagement pathways
that the surrogate has learned from past experiments.
```

So:

- If the new treatment moves short-run features that historically lead to higher retention, `Y_hat` rises.
- If it barely moves those features, `Y_hat` stays flat.
- If it moves engagement in a way historically associated with worse retention, `Y_hat` falls.

### 4. When the method is not functional

The method fails or becomes weak if:

1. There is **no historical labeled `Y`** at all, so Stage 2 cannot be trained.
2. The new experiment affects retention through a **new pathway** not captured by short-run `X`.
3. Past instruments were too weak or too narrow, so Stage 1 never learned useful variation.
4. We try to predict long-run impact **before any short-run behavior is observed**.

### 5. Practical recipe

```text
Offline once:
  use past experiments + past realized retention Y
  train Stage-1 / Stage-2 surrogate

Online for each new experiment:
  run short A/B window
  measure short-run X
  compute Y_hat by arm
  decide whether long-run retention is likely to improve

Later validation:
  after 2–4 weeks, compare Y_hat vs true Y
  retrain if the relationship drifts
```

## Bottom Line

> Combine user-level ML with randomized A/B assignments as instruments to build fast surrogate metrics for long-run outcomes. Stage 1 debias short-run engagement; Stage 2 maps that debiased engagement to the long-run target; deploy the Stage-2 model as a daily experiment metric. Historical `Y` is required only for training. For a new experiment, observe short-run `X` early and use `Y_hat` as the still-unknown long-run retention estimate.
