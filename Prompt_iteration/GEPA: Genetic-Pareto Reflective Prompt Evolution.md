# GEPA: Genetic-Pareto / Reflective Prompt Evolution

## Paper Link

https://arxiv.org/abs/2507.19457

## One-Line Summary
GEPA optimizes prompts by evolving a pool of candidates with reflective LLM mutations and Pareto-based selection, using rollout traces as natural-language feedback rather than scalar rewards alone.

## Core Problem
Standard prompt search often:

- keeps only one current prompt,
- uses only aggregate scores,
- underuses rich rollout traces / reasoning feedback,
- collapses diversity too early onto a single average-best candidate.

## Method
Treat prompt optimization as evolutionary search:

```text
1. Maintain a candidate pool of prompts
2. Evaluate candidates on tasks / examples
3. Select a parent from the Pareto frontier
4. Reflectively mutate using rollout traces + feedback
5. Minibatch-accept only if child beats parent
6. Fully evaluate and update the frontier
```

### Key ideas

**Candidate pool + score matrix**

```text
Track score(candidate, task/example), not only average score
```

**Pareto selection**

```text
Keep candidates that are best on at least some tasks
Sample parents from the frontier, weighted by how often they win
```

This preserves specialized prompts that solve different failure slices.

**Reflective mutation**

```text
current instruction
+ inputs
+ outputs / reasoning traces
+ evaluator feedback
+ score
-> rewritten instruction
```

Diagnosis and rewriting are usually collapsed into one reflection call.

**Optional merge/crossover**

Useful mainly for multi-module systems: combine complementary module-level changes from two parents.

**Stopping**

Typically budget-driven: number of reflective-mutation rounds / evaluation calls, then return the best average-scoring candidate.

## Concrete Example
Binary self-harm policy optimization with 3 candidates:

```text
P0: baseline policy
P1: better on euphemistic suicide language
P2: better on joke / sarcasm false positives
```

Pareto frontier may keep both `P1` and `P2` even if neither is best overall.

Next mutation might sample `P1`, inspect its remaining errors, and produce `P3` that improves another slice. The pool grows; final selection can still be the best average candidate, but search did not discard specialized winners early.

## Results
From prior comparisons in our notes / related papers:

- Strong automated reflective optimizer baseline.
- Often better than naive iterative human debugging loops.
- In the Clustering-based Prompt Opt paper, GEPA improved Vertical Quality held-out by `+16.67`, but still trailed the cluster loop (`+41.67`).
- On Vertical Candidate, GEPA gain was weaker / not robust (`+1.67`).

GEPA's strength is sample-efficient exploratory search when evaluation is affordable enough to maintain a pool.

## Relation to Our Research
What to borrow:

1. Optionally keep a small pool of 3-5 policies.
2. Track per-slice metrics, not only one aggregate score.
3. Use minibatch precheck before full train re-eval.

What not to import blindly:

- Full GEPA is evaluation-heavy.
- Whole-prompt rewrites are coarse for auditable policy rules.
- Pareto diversity matters less if we only ever ship one policy and evaluate one global metric.


## Bottom Line
GEPA is population-based reflective prompt evolution with Pareto diversity. Useful if we want broader search; for our current single-policy gated loop, SkillOpt-style controls and VISTA-style diagnosis are higher leverage first.
