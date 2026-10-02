# Automating Eval Design and Hillclimbing with Claude (claude-api skill, Anthropic)

## Paper Link
https://claude.dev/blog/automating-eval-design-and-hillclimbing/

Blog post / playbook (Lance Martin, Sep 28 2026), not a peer-reviewed paper. No ablations; two worked examples.

## Setup (read this first)

Two commands in the `claude-api` skill for Claude Code:

- `/claude-api build-eval`: Claude interviews you, builds an eval inside your repo (cases, grader, runner, results page), and stops for your approval at a few points.
- `/claude-api hillclimb`: Claude improves your app against that eval **one patch per round**, with a held-out split to catch overfitting.

The thing being edited is usually **text** (system prompt, skill, tool descriptions) or **config** (model, effort). The model weights never change. Same family as GEPA / SkillOpt / `training.py`; this post is mostly about **not fooling yourself** while doing it.

## One-Line Summary
Build an eval that tracks production, has headroom, and has low noise; then change one thing per round and keep it only if both train and held-out scores rise.

## Core Problem
Two failure modes. (1) A bad eval: tasks that are easy to grade but not what production needs, a grader that flips on the same output, no headroom, or noise larger than the gains you care about. (2) Overfitting while climbing: the eval leaks into the harness (a tool, a path, a phrase, one patch per failure you read), so the score goes up and production does not.

## Terminology

| Term | Plain meaning |
|---|---|
| Surface | What the hillclimber may edit: prompt, skill, tool descriptions, model / effort, harness code. |
| Headroom | Gap between the best model at highest effort and 100%. Needed to see changes. |
| Noise | How far the score moves by chance alone (repeat runs, grader flips). |
| Adversarial sampling | Picking cases because *today’s* model fails them. Warned against. |
| Checkable-claim rubric | Judge rubric of yes/no claims, not a 1–5 scale. |
| Blind pairwise judge | Judge sees baseline and candidate in random order, not told which is which. |
| Train / test split | Random split. Analyzer reads **train** transcripts only; test gates keep/revert. |
| Stall reflection | After 2–3 flat rounds: sort every remaining failure by cause, make no edit. |

## Method

**Four properties of a good eval.**

```text
1  mirrors production     sample what you care about, not what is easy to grade
2  scales with capability stronger model / more effort should score higher
                          (if not: ambiguous tasks or a miscalibrated grader)
3  passable headroom      frontier well below 100%, and not because tasks are impossible
                          (tell: a task fails every run regardless of replicates)
4  low variance           grader stable on identical output; config applied consistently;
                          no leftover state (files, git history) leaking answers
```

A good task: two domain experts would reach the same verdict, and everything the grader checks is stated in the task.

**Adversarial sampling trap.** Capability is jagged. Cases chosen because today’s model fails them sample **that model’s valleys**, so the eval measures one model’s failure fingerprint. Instead: pick cases a human can explain *why* they are hard, add real production failures (tickets, bug reports), and do not trust user traffic alone (users try what they expect to work, so it skews easy).

**build-eval.**

```text
inputs, in priority order
  1 production transcripts (after asking about retention / sensitive data)
  2 bug reports and support tickets
  3 5–10 hand-written cases
  4 cases synthesized from the codebase
  → review page, human confirms the inputs

grader = cheapest that fits
  constrained output → code check (exact match, label set, JSON schema, tests)
  open-ended         → LLM judge, rubric of checkable claims
                       vs a baseline: blind pairwise, random order
                       judge model ≠ model under test
  Claude grades a handful; asks "would you score any differently?"

baseline run with CI, plus diagnostics
  grader twice on the same output → did the verdict change?
  plumbing: timeouts, API errors, truncated answers
  headroom: baseline ≳ 95% → climb cost / latency instead of quality
```

**Choosing what to climb.** Cheap to change and revert (text beats open-ended harness rewrites). Attributable (e.g., skill-trigger rate is coupled to the skill description you edit). Well-scoped (a saturated eval or “improve the harness” stalls). Cost at equal quality is a strong default objective.

**Overfitting and the three guards.** Leaks: an OCR tool that only helps the eval mix; “always `cd /app`, run `pytest`” because eval tasks live there; a prompt tuned to distinctive eval phrasings; one patch per failure read; or `curl` of a public reference solution.

```text
split the cases              train readable by the hillclimber; test not read
never paste failures         read failing transcripts, but never copy their content into the prompt
answers out of reach         structurally, so the model cannot reward-hack
```

**hillclimb loop.**

```text
pick goal (quality, or cost at parity); pick editable surfaces
random split → train / test
check noise < smallest improvement you would act on   (else: more repeats or cases)

each round
  read previous train transcripts
  propose ONE root-cause patch (rewrite the section / add the missing rule, not reword a line)
  rerun
  train ↑ and test ↑   → keep
  train ↑, test flat    → suspect overfit, revert
  any regression        → revert

stall 2–3 rounds (or no single fix could beat noise)
  sort every remaining train failure by cause; no edit
  catches ambiguous cases, harness errors, variance
  only legitimate failures go into later rounds

end: code left at best-on-test version; report test vs baseline with CI
     gain within noise → recommend not merging
```

## Concrete Example

**Inbox router (the post’s toy).** 24 emails, route to a queue. Baseline mean correct $0.681$.

```text
v1  define each queue + add a tie-break rule   train 0.875  test 0.875   keep
v2  add two worked examples                    train ↑      test flat    revert
```

v2 is the classic leak: worked examples that look like the train emails lift train only.

**Noise check, in numbers.** With $n$ test cases and pass rate $p$, one case moves the score by $1/n$ and the standard error is about

$$
\mathrm{SE} = \sqrt{\frac{p(1-p)}{n}}
$$

For the support example below, $n=14$: one ticket is about $7$ pp, and at $p=0.9$ the SE is about $8$ pp. A $+12$ pp held-out gain is real-looking but not tightly pinned; that is why the skill checks noise before round 1.

**Ask analog.** Surface = the PINSAFE / A4 policy text. Split journeys into train / test. The editor may read train failures but must not paste pin text or user text into the policy. Keep an edit only if train and test must-refuse both rise and utility does not regress. After two flat rounds, stop editing and cluster remaining failures: judge flips, ambiguous labels, harness bugs, true policy gaps. Only the last bucket feeds more rounds.

## Results

**Cost-focused (internal support benchmark, 44 tickets: 30 search / 14 held out).**

```text
config                                 train acc   ¢ / ticket
Opus 4.8, high effort (baseline)       74.4%       4.6
prompt audit (drop mandatory tool-call rituals, scratchpad, contradictory rules)
Opus 5.5, low effort                   87.8%       1.9
Sonnet 5, low effort                   88.9%       ~1.0
+ routing rules, refund-cap cross-ref  98.9%       ~1.0

held-out 14:   78.6% → 90.5%   at about 1/5 the cost
```

Part of the saving is pricing: Opus 5.5 tokens are 20% cheaper and cache reads 60% cheaper than Opus 4.8.

**Performance-focused (the `claude-api` skill’s own eval, built from docs).**

```text
66%   baseline
74%   added sections for 8 missing features   (hillclimber had docs + SDK access)
77%   fixed C# / Java type tables
      stall → reflection: content was present, but Claude wrote OLD API shapes from priors
80%   migration table at top (fixed-budget thinking → adaptive; old web search / fetch → current);
      moved C# / Java warnings above examples
~88%  (87.9% at round 24) after fixing flawed tasks / graders + more skill edits
      e.g. task asked to catch 1 error type, grader wanted a chain of ≥3;
           a grader contradicted the docs, and the real API proved the docs right
```

## Relation to Our Work
- **Directly useful** for prompt / policy iteration. Same skeleton as `training.py`: evaluate → read failures → propose an atomic edit → gate → accept/reject. Three pieces map straight onto our wish list: one root-cause edit per round (atomic edits), stall → sort failures by cause (Clustering-based Prompt Opt’s diagnosis layer), and noise-before-round-1 (our bootstrap / McNemar gates).
- **Judge hygiene** lines up with Zalando and BinEval: rubric of checkable claims instead of 1–5, grader run twice on the same output, judge model ≠ tested model, read scored transcripts before trusting the grader. Blind random-order pairwise vs baseline is cheap to add to Eval Hub.
- **Adversarial sampling warning hits us.** `training.py` samples errors from the current policy. That is fine as **optimizer input** (train), but the **eval** set should not be built only from today’s failures, or it measures one policy’s fingerprint.
- **“Never paste failures into the prompt”** is the leak we worry about with policy editors: reading a failing image/pin is fine; copying its specifics into the policy is overfitting.
- Do **not** import blindly:
  - Their “test” is read by the gate **every round** and picks the final version. That makes it a validation set with a winner’s curse. SoL-Pi keeps EdgeBench fully outside the loop. Keep a third untouched split (our nested selection / confirmation folds).
  - 14 held-out tickets is small (one ticket ≈ 7 pp). The post says the tool reports CIs, but none are shown for the headline numbers.
  - Part of the skill-eval gain (80 → 88) came from fixing tasks and graders, which moves the ruler. Report “policy gain” and “eval fix” separately.
  - The cost win mixes a prompt audit, a model upgrade, and a price cut. Attribute each.
  - Vendor post: evidence is two internal examples with no baselines against other optimizers.

## Bottom Line
Most of the work is the eval: production-shaped, headroom, low noise, a judge you have checked. Then change one thing at a time, and keep it only if the split you did not read also moves, and keep one split the loop never touches.
