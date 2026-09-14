# Incremental Recommendation via Causal Models (Home Recommendations / Causal ML, Spotify)

## Paper Link
https://arxiv.org/abs/2608.26804

## Spotify logic (read this first)

You do not need a Spotify account. Think of **Home** as the first screen after you open the app: a feed of cards (“try this album,” “new episode”). Each card is a **recommendation** (the paper’s “rec”). Only a few cards fit. Showing one card means not showing another. That showing is an **impression**.

**Stream** = the user actually **presses play** on that album / track / show. Not “they saw the card.” Play.

Two ways a play can happen:

```text
Shown:   Home puts the Taylor card on screen → they tap it → play
Hidden:  Home does not show that card → they still find Taylor
         (library, search, “new from artists you follow”) → play
```

The second path is **organic**: they got there without this card.

**Holdback** is not a model. It is an **A/B-style coin flip Spotify already runs**: for a random slice of (user, album) pairs, they **do not show** the card, on purpose, so they can watch whether that person still plays the album. Those people are the holdback group. Everyone else who was eligible and *did* see the card is the **shown / treated** group.

From those two groups they train two **probabilities** for the same (user, album). Each is a number in $[0,1]$: “how likely is a play?” The hat means a model estimate, not a count.

| Name | Question in English | Clock they use to count a “yes” |
|---|---|---|
| $\hat{p}_1$ | If we **show** the card, what is $P(\text{play})$? | Minutes to hours after the card (they treat it as a response to the card) |
| $\hat{p}_0$ | If we **hide** the card (holdback), what is $P(\text{play})$ anyway? | Up to **two days** (organic discovery is slow) |

$\hat{p}_1$ high + $\hat{p}_0$ high = **always-taker**: they will play whether you waste the slot or not (fan who checks Taylor every Friday).  
$\hat{p}_1$ high + $\hat{p}_0$ low = **incremental**: the card is how they find it.

You **cannot** do $\hat{p}_1 - \hat{p}_0$ and call that “extra plays caused by the card.” A play in 20 minutes after a tap is not the same event as a play sometime this weekend with no card. Different stopwatches. That is why the paper refuses the usual CATE subtraction.

## One-Line Summary
Only show the Home card when $\hat{p}_1$ is high **and** $\hat{p}_0$ is low — the card would get a play, and they would not have found the album alone. Do not subtract the two scores.

## Core Problem
Home slots are scarce. The old model only maximizes $\hat{p}_1$ (“will they play if we show it?”). That loves always-takers and wastes the slot.

Holdback already answers “would they play if we hide it?” ($\hat{p}_0$). The trap is using that answer as if it were on the same clock as $\hat{p}_1$. A leftover messiness: about 30% of “we decided to show it on the server” never become a card on the phone, so the two training sets are not even the same population.

## Terminology

| Symbol | Plain meaning |
|---|---|
| $x$ | This user + this album (features). |
| $T = 1$ / $T = 0$ | Show the card / hide it (holdback). |
| $Y(1)$, $Y(0)$ | Did they play, if shown / if hidden. |
| $\hat{p}_1(x)$ | Predicted $P(\text{play} \mid \text{we showed the card})$, short clock. |
| $\hat{p}_0(x)$ | Predicted $P(\text{play} \mid \text{we hid the card})$, two-day clock. |
| $\theta_1, \theta_0$ | Cutoffs: show only if $\hat{p}_1 \ge \theta_1$ and $\hat{p}_0 \le \theta_0$. |
| $\tau(x)$ | Textbook “extra play from showing” — **not** $\hat{p}_1 - \hat{p}_0$ here. |

## Method
Start from the live multi-task shared-trunk net (trained only on treated data, primary head $\hat{p}_1$). Add a **holdback head** $\hat{p}_0$ — a Deep Twin / DragonNet-style pair of outcome heads, no propensity head (assignment is randomized).

Partitioned loss: treated examples update only the treated head + trunk; holdback examples update only the holdback head + trunk. Do not let holdback labels train $\hat{p}_1$ (that would mix the two windows).

Serve only if both gates fire:

$$
\pi(x) = \mathbf{1}[\hat{p}_1(x) \ge \theta_1] \cdot \mathbf{1}[\hat{p}_0(x) \le \theta_0].
$$

$\theta_0$ is the efficiency knob: raise it to drop more always-takers; set it to $0$ and you are back to the production $\hat{p}_1$-only policy. Thresholds are set offline on randomized data for an impression-cut target plus non-inferiority on consumption.

```text
p̂₁ high, p̂₀ low   →  incremental: show
p̂₁ high, p̂₀ high  →  always-taker: withhold
p̂₁ low            →  won't convert anyway: withhold
```

## Concrete Example
Home slot. Two users, same new Taylor Swift album.

```text
Alex  already follows Taylor, checks Friday drops.
      p̂₁ = 0.85   (will stream if shown)
      p̂₀ = 0.80   (will stream this weekend anyway)
      dual-threshold: WITHHOLD. Impression is not incremental.

Sam   does not follow Taylor. Discovers via Home or not at all.
      p̂₁ = 0.40
      p̂₀ = 0.05
      dual-threshold: SHOW.
```

Naive CATE `0.85 − 0.80 = 0.05` vs `0.40 − 0.05 = 0.35` looks directionally similar, but those differences are **not** treatment effects: Alex’s `p̂₀` is “streamed sometime in two days,” Alex’s `p̂₁` is “streamed in the next hour after the card.” You cannot subtract them.

Ask-Pinterest analog: do not spend a hero pin on a user who would have hit the same pin in organic Home. Show it when `P(engage | Ask shown)` is high and `P(engage | Ask withheld)` is low.

## Results
Live Home A/B, millions of users, two weeks. Three arms: production `p̂₁`; causal model but still `p̂₁`-only (isolates joint training); causal model + dual threshold.

Treatment-Causal vs Treatment-Model (same architecture, policy differs):

```text
impressions / user:              −7.1%   [−7.2%, −6.9%]
recommended-content consumption: −0.37%  [−0.86%, +0.21%]   (n.s.)
```

They read this as: ~93% of production Home impressions were already incremental; the policy removes the non-incremental 7%. Guardrail: no significant hit to listener satisfaction.

Joint training also **calibrates** `p̂₁` better than the treated-only baseline (especially at high scores). Their story: the trunk must represent organic affinity, so the treated head stops over-predicting always-takers. Holdback head is calibrated too, noisier in the tail (smaller `D₀`).

## Bottom Line
Do not subtract treated minus holdback when the clocks differ. Keep both scores and only spend the impression when the rec is likely to work **and** the user would not have gotten there alone.
