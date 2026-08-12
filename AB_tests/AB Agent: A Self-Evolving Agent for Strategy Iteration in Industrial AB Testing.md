# A/B Agent: A Self-Evolving Agent for Strategy Iteration in Industrial A/B Testing

## Paper Link
https://arxiv.org/pdf/2608.04625

## One-Line Summary
A/B Agent turns fragmented historical A/B strategies into a hierarchical experience tree, retrieves transferable strategies with Tree-RAG, and iteratively tunes them online using A/B feedback under core + guardrail metrics.

## Core Problem
Industrial recommender strategy iteration is still mostly human-driven:

- engineers manually design strategies, launch A/B tests, analyze results, retune parameters;
- historical experiment knowledge is fragmented across docs/code/configs/logs;
- flat RAG often retrieves the wrong scenario/stage/objective, so transfer is weak;
- one-shot RAG suggestions lack a closed loop from generation ? experiment ? refinement ? knowledge writeback.

## Method
Three coupled components:

```text
1. Historical Strategy Knowledge Organization
2. Autonomous Target-Aware Strategy Generation
3. Experiment-Guided Strategy Self-Evolution
```

### 1. Knowledge organization
Convert each historical experiment into atomic strategy chunks:

```text
motivation, mechanism, parameters,
applicable context, outcomes, risks
```

Organize into a hierarchical experience tree:

```text
domain ? scenario ? ranking stage ? optimization objective
```

### 2. Strategy generation (Tree-RAG)
Given a request like improve Short-Video Cart GMV at MixRank without hurting engagement:

```text
parse scenario / stage / target / guardrails
? multi-path sparse + dense retrieval
? hierarchy-aware boosting + reranking
? generate executable strategy + params
? agent/human feasibility & safety checks
```

### 3. Self-evolution
After launch, build an experiment tree of successive variants. Utility balances core gains vs guardrail harm:

```text
U(v) = sum_j w_j * ?core_j
     - ? * sum_k w_k * max(0, -?guard_k)
```

Then:

- if a branch works ? local parameter search,
- if saturated / guardrails fail ? retrieve alternative mechanisms,
- write validated outcomes back into the experience tree.

## Concrete Example
Request:

```text
Improve Short-Video Cart GMV at MixRank
without hurting user engagement / Live GMV
```

Agent retrieves related historical strategies (e.g., interest-score fusion, CTR boost with tunable weight), proposes:

```text
Strategy: GMV-aware CTR boosting
Initial weights: w = 1.0, 2.0, 5.0
```

Online evolution (simplified from Table 3):

```text
S1: GMV +1.12%, guardrails hurt
S2: GMV +2.98%, still risky
S3: GMV +3.30%, guardrails mostly recover
S4: GMV +3.25%, all guardrails non-negative
S5: GMV +4.83%, GPM +4.68%, all guardrails positive
```

Final strategy beats the expert baseline on primary GMV/GPM while avoiding the expert�s negative Watch Time / Live GMV effects.

## Results
Offline (3 Kuaishou e-commerce scenarios, 310 strategies):

```text
Overall score: 7.244
vs Claude-Sonnet-4.6: +1.3%
vs best RAG per scenario: +25.0% / +31.7% / +23.5%
```

Online deployment:

```text
GMV  +4.829%
GPM  +4.677%
OPM  +0.841%
CVR  +0.578%
```

Ablation: knowledge base removal hurts most; scenario-aware boosting / multi-path retrieval / reranking also matter. Flat RAG is only slightly worse than Tree-RAG offline, but hierarchy still helps.

## Relation to Our Research
**Adjacent, not a direct replacement for our policy-optimization loop.**

Closest mapping:

| A/B Agent idea | Our loop analogue |
|---|---|
| Hierarchical experience tree | Policy/failure-mode memory across categories/surfaces |
| Atomic strategy chunks | Atomic policy edits |
| Guardrail-aware utility | Validation gates / anti-regression constraints |
| Experiment-tree self-evolution | Iterative accept/reject + writeback of what worked |
| Writeback of validated outcomes | Rejected-edit buffer + accepted-rule changelog |

Useful takeaways for us:

1. Organize historical optimizer outcomes hierarchically (policy category � surface � failure mode), not as a flat prompt dump.
2. Treat accepted/rejected policy edits as transferable �strategy chunks.�
3. Explicitly optimize a core+guardrail utility, not a single metric like F1.
4. Closed-loop writeback after each gated iteration is the real productization win.

What we should **not** import blindly:

- Their target is ranking/strategy parameter search for GMV, not LLM rubric/policy text optimization.
- Their �A/B experiment tree� assumes many online experiments; our loop is mostly offline label/policy iteration plus occasional audits.
- Offline evaluator is another LLM (GPT-5.5), so strategy-quality scores may be optimistic.

Relative to papers we already reviewed:

- Closer to SkillOpt / GEPA-style iterative improvement than to HUMBR.
- Shares �atomic unit + validation + memory� with the Clustering Prompt Opt paper, but at recommender-strategy granularity.

## Bottom Line
A/B Agent is a closed-loop industrial agent for reusing and evolving A/B strategies under guardrails. For us, the transferable idea is hierarchical experience + atomic edits + guardrail-aware utility + writeback�not the recommender GMV objective itself.
