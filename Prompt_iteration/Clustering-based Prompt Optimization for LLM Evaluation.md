# Clustering-based Prompt Optimization for LLM Evaluation

## Paper Link

https://kdd-eval-workshop.github.io/agenticai-evaluation-kdd2026/assets/papers/71_Clustering_based_Prompt_Opt.pdf

## Core Idea

This paper studies how to optimize an LLM evaluator rubric when human labels and LLM evaluation calls are expensive. The target is not general task accuracy, but **human-AI agreement**: the LLM judge should reproduce expert human ratings as closely as possible.

The main proposal is a **cluster + batch-validate loop**. Instead of repeatedly showing a small set of errors to an LLM and asking it to rewrite the rubric, the method first evaluates the baseline rubric on the training set, collects all baseline disagreements, clusters those disagreements into recurring failure modes, and then creates one atomic rule per stable failure mode.

The workflow is:

1. Evaluate the baseline rubric `v0` on the training set.
2. Collect all misaligned examples where the evaluator disagrees with human labels.
3. Run the clustering/proposer LLM multiple times on the same error pool, using different shuffles and prompt framings.
4. Convert the multiple clustering outputs into consensus failure-mode clusters.
5. Generate one atomic rubric rule per stable cluster.
6. Evaluate each single-rule candidate independently.
7. Accept a rule only if it passes statistical and regression gates.

The important design principle is:

> Clustering is used for diagnosis, not acceptance. A cluster only proposes a possible policy/rubric gap; the candidate rule still has to pass evaluation gates before it is trusted.

## How Clustering Works

Each clustering run is not a training iteration. A clustering run means re-processing the **same error pool** with a different seed, input order, or prompt framing.

For example, suppose iteration 1 produces `X` misaligned examples. The paper does not wait for many optimization iterations to identify clusters. Instead, it runs several clustering calls on those same `X` examples:

```text
Same X misaligned examples
  -> clustering run 1
  -> clustering run 2
  -> clustering run 3
  -> ...
  -> consensus clusters
```

A pair of examples is considered stably related if they are placed in the same cluster in most runs, for example `(N - 1) / N` clustering runs. Unstable one-off groupings are discarded as proposer noise.

A practical version is:

```text
A_ij = fraction of clustering runs where example i and example j are grouped together

if A_ij >= threshold:
    connect i and j

consensus clusters = connected components of the stable co-membership graph
```

This makes the LLM clustering output less fragile than relying on one clustering call.

## Why This Is Useful

The method improves over a simple iterative prompt-debugging loop because it changes the unit of optimization.

Instead of:

```text
small error slice -> bundled prompt rewrite -> hard-to-attribute gain/loss
```

it uses:

```text
full disagreement pool -> recurring failure mode -> one named rule -> independently validated gain/loss
```

This gives better interpretability, rollback, and debugging. If a rule later causes harm, it can be removed without reverting an entire bundled prompt update.

## Reported Results

The paper compares three methods:

- linear human-debugging loop,
- GEPA-style reflective prompt evolution,
- cluster + batch-validate loop.

The cluster method performs best on both evaluator tasks:

```text
Vertical Candidate:
  linear:  +0.67
  GEPA:    +1.67
  cluster: +6.00

Vertical Quality:
  linear:  +9.52
  GEPA:    +16.67
  cluster: +41.67
```

The cluster loop is the only method robustly positive on both tasks.

## Concern 1: Cost of Multiple Clustering Runs

One concern is that running `N` clustering calls inside one iteration can be expensive, especially if each example contains images, long traces, or large context.

This concern is valid. The paper treats clustering calls as cheaper than full evaluator passes, but that may not hold in our workflow if each misaligned sample is expensive to serialize and send to an LLM.

A practical way to control cost is to split diagnosis into two stages:

```text
Stage 1: compress each error into a short failure summary
Stage 2: cluster only the summaries, not the full raw examples/images
```

For example:

```text
Example ID: abc
Ground truth: unsafe
Model prediction: safe
Failure summary: missed indirect self-harm encouragement
Key evidence: euphemistic suicide wording
Confidence: high
```

Then clustering operates on compact text summaries. The original samples are only retrieved when generating or validating a rule.

Other cost controls:

- use a small number of clustering runs, e.g. `N = 3` instead of `N = 5`;
- cluster only high-gradient or high-impact errors first;
- use embeddings or cheaper models for initial grouping;
- require minimum weighted support before asking the LLM to draft a rule;
- cache per-example failure summaries across iterations;
- run full multi-seed clustering only when the error pool is large enough.

So the recommended view is:

> Multi-run clustering is useful when the error pool is large enough to contain recurring patterns. If the pool is small or expensive, first compress errors, then cluster summaries under a fixed budget.

## Concern 2: Clusters May Be Sparse

Another concern is that after several iterations, the remaining errors may become sparse:

```text
X misaligned examples
Y clusters
Y is close to X
```

In that case, clustering does not reveal reusable failure modes. Most errors may be idiosyncratic, ambiguous, label-noisy, or too rare to justify a new policy rule.

This is an important signal. If `Y` is not much smaller than `X`, we should not force the optimizer to create many rules. Instead, we should treat it as a stopping or triage condition.

Possible interpretations:

1. **No dominant policy gap remains.**  
   Earlier iterations fixed the common failures, leaving only tail cases.

2. **Labels may be noisy.**  
   If the model is consistently confident against the supposed ground truth, some examples may need human re-adjudication.

3. **The policy lacks features/context.**  
   Some errors cannot be fixed by prompt text alone because the model lacks required information.

4. **The clustering granularity is too fine.**  
   The cluster prompt may need to ask for higher-level conceptual groups rather than surface-level differences.

5. **The dataset is too small.**  
   More examples may be needed before a stable rule can be justified.

Recommended rule:

```text
Only generate a candidate rule if a cluster has enough support.
```

Support can be measured by:

```text
cluster_size >= minimum_count
weighted_support >= threshold
average_gradient_priority >= threshold
bootstrap evidence stable
```

If no cluster passes support thresholds, the iteration should probably stop, collect more data, or route suspicious examples to human review.

## How This Would Fit Our Training Loop

For our policy optimization workflow, the clustering step should sit between evaluation and policy rewriting:

```text
1. Evaluate current policy on training set
2. Collect misaligned examples
3. Generate compact failure summaries
4. Cluster failure summaries into recurring policy gaps
5. Keep only clusters with stable support
6. Generate one atomic policy update per cluster
7. Evaluate each candidate policy update
8. Accept only if the validation/gate criteria pass
```

The key modification from the paper is that we should add explicit cost and sparsity controls:

```text
if error_count < minimum_error_count:
    skip clustering

if cluster_support is too sparse:
    do not generate rules
    send repeated high-confidence disagreements to human review

if clustering cost exceeds budget:
    cluster summaries, not full raw examples
```

## Bottom Line

The paper’s idea is strong because it converts noisy individual errors into auditable, reusable prompt rules. However, it should not be applied blindly.

The practical version should be:

> Use clustering when there are enough errors to reveal recurring failure modes. Treat clusters as hypotheses, not truth. Generate rules only for clusters with meaningful support. If clusters are sparse, stop optimizing or route examples to human review instead of creating overfit rules.
