# On Evaluating and Improving Conversational Agents in Production (Shopping Assistant, Zalando)

## Paper Link
https://arxiv.org/abs/2609.32092

## Zalando logic (read this first)

**Assistant:** a multi-agent shop bot (20+ EU markets, millions of chats / month). User: “navy trainers.” Agents search, curate a **carousel**, ask a follow-up.

* You **cannot** replay yesterday’s log against a patched prompt. If the bot’s first reply changes, the user’s next turn is not the old transcript. 
* The **unchanged** bot also jitters: LLM sampling, catalog, prices, personalization. 
* A single “quality” score hides **which** behavior broke.

They **commission** one investigation for a **named** bug: freeze a **cohort** of starts and **assertions** (pass/fail the LLM judge can check), simulate the customer **forward**, compare patch vs stored baseline with **paired** bootstrap. The judge is **software**: they audit its inputs and config. After the case, the harness may change — **human-approved**, future-only.

**Not SFT, not a human on every thumbs-down.** They do not mine later turns, summarize “user wanted size-42 runners,” and lock that string as the gold reply to `navy trainers`. Better = higher assertion pass rate, not closer to a logged sentence. A human does **not** jump on every `not for me`. That line is only a hint the bug exists. Humans review the **exam** once (draft assertions / cohort → freeze), then again only if a patch is already signal+. The LLM judge ticks every simulated session.

**Three problems, one chat.** Men’s context, user types `navy trainers`. Prod carousel: men’s runner, **women’s navy heel**, men’s boot. User: “not for me.”

*Problem 1 — cannot replay.* Old log is `navy trainers` → “great for a night out” → `not for me`. Replay those two user lines against a new prompt that now shows only men’s runners + “want a 42?” The old `not for me` is nonsense (they never saw the heel). You are scoring a conversation that would not happen. Keep only the **start**; a simulator writes a new turn 2. (`want a 42?` is an invented patched reply; size 42 is account context, not inferred from `not for me`.)

*Problem 2 — even the old prompt jitters.* Same start, unchanged bot, three runs: FAIL / PASS / FAIL. Baseline 1/3. One lucky PASS on the new prompt is not a ship. Pair: per scenario $\Delta$ = mean(new) − mean(old), then bootstrap.

*Problem 3 — one quality number hides which behavior.* Session quality 3.0 → 3.9 does not say category vs gender vs latency. Named assertions do: first product is a men’s trainer? / all products? / reply under 3s? / women’s-context guardrail? Profile tells the editor **where** it broke.

Freeze = lock that exam (starts + pass/fails + judge inputs) and the control scores **for this case**. Simulate-forward = new user turns are OK. Pair-bootstrap = don’t confuse jitter with a patch.

## One-Line Summary
Don’t replay chats or chase one quality number: freeze assertions + a scenario cohort, simulate forward, pair-bootstrap the patch, and treat the judge as a system you test.

## Core Problem
Offline eval of a live conversational agent fails three ways: logs are not replayable, the control arm is stochastic, and an aggregate score does not say what to edit. Prompt-opt / auto-research on the **same** examples you score overfits the eval. Need a frozen commission, a gate that respects run-to-run noise, and a wall between “this investigation” and “next harness version.”

## Terminology

| Symbol | Plain meaning |
|---|---|
| Commission | Frozen package: cohort, assertions, evidence fields, thresholds, stored baseline. |
| Cohort | Fixed scenarios that can show the target failure. Not a traffic sample. |
| Assertion | Versioned pass/fail the judge applies (plus guardrails). |
| Session / run | One simulated chat / one pass over the whole cohort. |
| Grounded sim | First user line from the log; later user turns are **generated**, not replayed. |
| Stored baseline | $\ge 3$ runs of the **unchanged** local assistant on that cohort. |
| Paired $\Delta$ | Per scenario: mean(patch) − mean(baseline). Scenario is the unit. |
| signal+ / − / noise / borderline | Bootstrap CI entirely $>0$ / $<0$ / contains 0 and narrow / contains 0 and wide. |
| Orchestrator | Proposes isolated prompt/tool/code edits; autonomy budget caps how many. |
| Task-completion | 1–5 judge score of the whole session (often a **guardrail**, not the target). |

## Method

```text
reported bug
  → harness writes assertions + cohort (human reviews, then FREEZE)
  → reproduce locally; if assertions do not fail, STOP
  → ≥3 runs of unchanged system = baseline
  → orchestrator: isolated edit (prompt / tool / code)
  → same # runs of the patch
  → per-scenario Δ, 2000-resample percentile bootstrap
  → advance only if target = signal+ AND no guardrail = signal-
     AND a second eval repeats that
  → human review, maybe online A/B
  → AFTER the case: optional harness revision (human, future-only)
```

Noise threshold (set **before** any patch): half-width $\le 0.05$ on a 0–1 assertion, $\le 0.25$ on a 1–5 score. Borderline $\to$ more runs, not “mean looks up.” Stop at the **first** reproducible win so they do not grind the frozen cohort.

Judge cost dominates (input tokens). One 3-turn session $\approx$ 4k sim + 13k task-score + 6k **per assertion**. Category case $\sim$ 10M tokens.

## Concrete Example

Assertions vs gold text, on that same chat:

```text
old bot:  [heel, runner, boot] + “great for a night out”   A1 FAIL (slot 1 is a heel)
new bot:  [runner, runner, boot] + “want a 42?”            A1 PASS
```

“Night out” vs “want a 42?” is **never** compared as text. The heel vs the runner is. `not for me` is thrown away as a script.

Human sit-down (investigation, not per message):

```text
prod: many chats look bad  →  open ONE case for that named bug
      harness drafts assertions + cohort
      human reviews the exam, FREEZE
      simulate / patch / bootstrap
      human again only if signal+
```

**Category.** Logs: carousel mixes in the wrong department. 51 production-grounded scenarios, four assertions of increasing strictness (any / first / $\ge$75% / all products in-category). Baseline: first product 83% in-category; all products 64% — about **one in three** carousels dirty **on this failure-selected cohort**. Fix: curation prompt, “may prefer category” $\to$ “must not return off-category” (still a prompt, not a hard filter). First-product $+6$ pp, all-products almost flat $\to$ the bug was **slot 1**, not the whole set. Shipped from run means **before** they had the paired rule.

**Gender.** No good logs. 9 gender-silent “men’s context” scenarios + 1 women’s guardrail. h1 = fix the tool description (borderline). h2 = bind shopping context in **another** agent’s system prompt: first-product $0.73 \to 1.00$, CI $[+0.067,+0.511]$, signal+; reproduced on 3 more runs.

**Judge as software.** One assertion was blind until they added product fields. Temperature was set to 0 in config but **never sent** to the API. Scores looked fine. They treat those as eval bugs, not model wins.

Ask analog: do not replay a PINSAFE transcript against a new A4 prompt. Freeze “must-refuse / utility” assertions + a cohort of journeys, simulate the user forward, pair-bootstrap vs the stored baseline. Do not edit the rubric mid-loop (`training.py` / SkillOpt on the same slice). Audit that the judge actually saw the pin JSON and the temperature you think you set.

## Results

```text
category (50 scen, 3 runs, pre-paired):
  first product  0.833 → 0.893   (+0.060)   shipped
  all products   0.640 → 0.647   (~0)       profile: prominent slots
gender (9 scen, 5 runs, paired):
  h1 first prod  +0.067  CI crosses 0   borderline
  h2 first prod  +0.267  [+0.067, +0.511]  signal+  (confirmed)
lessons: pair by scenario; test the judge; freeze eval during the case
post-hoc: betting interval on h2 with n=9 is weaker than percentile bootstrap
```

Cohort is **failure-enriched**. Pass rates are not production prevalence.

## Relation to Our Work
- **Directly useful** for LLM-as-judge **and** prompt iteration. Same skeleton as `training.py` / SkillOpt / EvoPilot: diagnose $\to$ isolated edit $\to$ gate $\to$ maybe ship. Closest to EvoPilot’s “admit a pair, not a green job,” plus Zalando’s **judge-as-software** lesson. SkillOpt edits a skill.md; they edit assistant prompts/tools; the **gate** is paired bootstrap on frozen assertions, not “mean score up.”
- Plug-in: Eval Hub. One behavior = one commission. Assertions at several strictness levels (any / first / all) so A4 profiles *where* it fails. Store a multi-run baseline. Second confirmation eval before human review. Harness/rubric change only after the case, human-approved (same wall as SoL-Pi’s EdgeBench / EvoPilot’s round $n$ ⇏ $n+1$).
- Do **not** import blindly: category ship predates the paired rule. $n=9$ is weak (they say percentile bootstrap under-covers; a betting CI would have been borderline). No multiplicity bound when the orchestrator keeps inventing hypotheses (autonomy budget is a cap, not a p-value). Judge model and temperature **changed across** investigations; that is not in the CI. Cost is $\sim$10M tokens for one small category study. Failure-selected cohort $\neq$ how often the bug hits production — do not treat assertion lift as a north-star A/B.

## Bottom Line
A chat log is not a test set. Freeze what “pass” means, simulate the next user turn, pair the noise, and audit the judge like you audit the bot.
