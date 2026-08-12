# SkillOpt: Bounded Text-Space Optimization for Agent Skills

## Paper
 
https://arxiv.org/abs/2605.23904

## One-Line Summary
SkillOpt treats a skill/policy document as a trainable text artifact and optimizes it with deep-learning-style controls: bounded edits, validation gates, rejected-edit memory, and epoch-wise slow/meta updates.

## Core Problem
Free-form prompt rewriting is unstable:

- the optimizer may rewrite too much at once,
- useful rules get accidentally deleted,
- failed edits are forgotten and repeated,
- short-horizon gains overwrite long-horizon lessons.

SkillOpt asks: how do we train an external text artifact as if it were model parameters, without updating the underlying LLM weights?

## Method
Keep the target model frozen. Optimize only the external skill/policy text.

Analogy:

```text
skill document      -> model parameters
trajectory feedback -> gradient / evidence
edit budget         -> learning rate
validation gate     -> held-out selection
rejected edits      -> negative optimization memory
slow/meta update    -> long-horizon optimizer state
```

### Algorithm sketch

```text
for each epoch:
  for each step:
    1. Roll out current skill on training tasks
    2. Split trajectories into failures and successes
    3. Optimizer proposes structured edits from minibatches
    4. Merge / rank edits
    5. Apply at most L_t edits  (textual learning rate)
    6. Evaluate on held-out selection set
    7. Accept only if score strictly improves; else store rejected edits

  At epoch end:
    write slow-update guidance + optimizer meta-skill from improvements/regressions
```

### Key controls

**Bounded edits**

```text
ADD / DELETE / REPLACE / INSERT
max edits per step = L_t
```

**Validation gate**

```text
accept iff selection_score(candidate) > selection_score(current)
```

Ties rejected.

**Rejected-edit buffer**

Failed updates become negative feedback for future optimizer calls.

**Success + failure evidence**

Failures propose corrective edits; successes propose preservation / anti-regression edits.

**Epoch-wise slow/meta update**

Compare consecutive skill versions on the same tasks; summarize:

```text
improvements
regressions
persistent failures
stable successes
```

into durable guidance.

## Concrete Example
Current skill/policy for self-harm labeling.

Rollout failures:

```text
misses euphemistic 'unalive' language
overblocks medical education content
```

Optimizer proposes 5 edits, but `L_t = 2`, so only top 2 apply:

```text
REPLACE: broaden euphemism coverage
ADD: medical-education exception with evidence requirements
```

Candidate fails validation because the exception is too broad. Store rejected edit:

```text
Do not broaden medical exception without requiring clinical context cues.
```

Next iteration avoids that direction and proposes a narrower exception that passes the gate.

## Results
From prior review / team discussion:

- People noted `policy_opt.py` is implemented more like SkillOpt than like GEPA/VISTA.
- The value is less about flashy search and more about stable, controllable text-space training.
- Best suited when one reusable artifact must improve over many iterations without destructive churn.


## Bottom Line
SkillOpt is the best architectural template for our current single-policy loop: keep one artifact, bound the edits, gate acceptance, remember failures, and accumulate slow long-horizon guidance. Add VISTA-style hypothesis separation and optional GEPA-style pools later if needed.
