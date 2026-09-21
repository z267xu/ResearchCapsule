# SoL-Pi: Recursively Scaling Auto-Research Loops for Efficient Agent Harness (Efficient Agents, NVIDIA / MIT / NTU)

## Paper Link
https://arxiv.org/abs/2609.20519

## Harness logic (read this first)

The **model** (GPT / Claude) is frozen. The **harness** is everything around it: tools, when to compact the chat, how tool output is stuffed back into context, whether “edit file + run tests” is one API call or two. Claude Code / Codex / Pi are harnesses. Long jobs die on **tokens**, not on a missing layer in the net.

SoL-Pi does **not** fine-tune the LLM. A second “research” agent watches traces, writes **harness patches**, and keeps only patches that stay capable and get cheaper. Think RUSH, but the artifact is **wrapper code**, not a policy markdown.

Search and final score are walled off. EdgeBench never goes back into the loop. That is the whole paper’s anti-overfit move.

## One-Line Summary
Auto-research ~150 harness ideas on ~500 hidden coding environments; freeze four survivors; they match Pi’s score on a held-out bench with ~half the tokens.

## Core Problem
Long-horizon agents waste tokens: extra model rounds, growing context, the same 50 KB log pasted every turn. Humans inspect traces and hand-edit the harness. Local wins break later steps. Prior auto-harness work overfits the search tasks. Need reusable efficiency **mechanisms**, not a prompt that only wins on the repo you tuned on.

## Terminology

| Symbol | Plain meaning |
|---|---|
| Harness | Frozen-model wrapper: tools, context, compaction, observation shaping. |
| Base / Pi | Starting coding harness they patch. |
| Research AI | Optimizer that proposes and implements harness changes. |
| Lineage | Isolated copy of the research loop for one idea; disposable. |
| Capability gate | Score stays inside a **pre-declared** tolerance. Agent cannot rewrite the bar. |
| Efficiency gate | At least one cost/token metric must improve. |
| EdgeBench | Held-out eval (51 public tasks). Frozen harness only. No search feedback. |
| Action Fusion | One tool call = edit + follow-up command (test/build). |
| Online Context Compact | Compact only when a plan step ends **and** estimated savings beat cache-rewrite cost. |
| ObservationPack | Big tool output: full for 2 turns, then handle + 1 KB excerpt. |
| Evidence-Preserving Reducer | Cheap model summarizes build/test logs; schema/hash check or fall back to raw. |

## Method
Fix metrics **before** search. Capability tolerances and efficiency metrics are not under the optimizer’s control.

```text
outer: 152 ideas in 6 families
       (context, progress, tools, delegation, prompt/policy, eval)
       Oracle Analysis on old traces → drop empty ideas

inner: one disposable lineage per idea (skill template + Ralph loop)
       propose → implement → reviewer → run
       analyzers: repeated actions / context growth / huge observations
       keep / revise / kill  (does not touch other lineages)

gate:  capability OK  AND  some efficiency up
       keep the nondominated set
combine four survivors → tune a bit → FREEZE
held-out EdgeBench  (never comes back)
```

Search set: 535 envs (495 GitHub issue/PR with hidden tests that fail-then-pass; 40 verifier-only). ~3,000 runs, >60k interactions. They do **not** claim a scaling law from those counts.

Action Fusion case: 27 iterations. Prompt-only “please fuse edit+test” was flaky; they **changed the tool schema** so the fused action is a first-class call, then tuned trigger rate as an intermediate metric.

## Concrete Example
Agent edits `foo.py`, then wants `pytest`. Naive harness: three model rounds (edit, think, run). Action Fusion: one request, one observation. If it must *see* the edit first, keep them split.

A 200 KB pytest log: Reducer writes a short receipt (exit code, failing asserts, quotes). Verifier checks hash/schema/size. Fail → raw log. ObservationPack then stops re-pasting the blob after two turns.

Ask analog: do not APO the judge prompt to “be cheaper.” Patch the **Ask harness** — fuse pin-search + CFS check, compact only at subtask end, stash huge pin JSON behind a handle. Gate: safety/capability within tolerance **and** tokens down. Do not tune on the eval slice you will report.

## Results
EdgeBench vs Pi (GPT-5.6 Sol), harness frozen:

```text
                    tokens vs Pi    cost vs Pi    score
SoL-Pi Efficiency   −49.0%          −33.2%        42.0 vs 44.8 (93.7%)
SoL-Pi Performance  −6.1%           (eff +9.8%)   47.2 vs 44.8 (+5.3%)
                    (Performance = ObservationPack alone on this backend)
```

Abstract: vs Codex / Claude Code native harnesses, ~45–49% less token traffic, ~1/3 API cost; they quote ~$8.75–$13.50/hour vs those natives, ~$4–$6/hour vs Pi. Same four mechanisms transfer to Opus 5 without a rewrite.

Terminal-Bench 4 (63 CPU tasks): Pi 18 solved, SoL-Pi **15**, cost −26% vs Pi. IMO 2026 Lean: 3/6 pass, cheapest $ per pass. Efficiency generalizes; **absolute solve count can drop**.

## Relation to Our Work
- **Directly useful** for prompt / harness iteration. Same skeleton as `training.py` / SkillOpt: roll out → diagnose traces → propose an atomic change → gate → accept/reject. GEPA reflects into **prompts**. SkillOpt edits a **skill.md**. SoL-Pi edits **harness code** (tools, compaction, observation). Closest sibling is SkillOpt’s bounded edit + reject memory; they add **isolated lineages** and a hard wall between search and held-out.
- Plug-in: treat Ask / PINSAFE wrappers (tool schema, context pack, when A4 is called) as the skill document. Pre-declare a capability band (must-refuse / utility) so the optimizer cannot buy tokens by going silent. Keep Eval Hub frozen the way they keep EdgeBench frozen.
- Their dual gate (capability tolerance **and** efficiency) is closer to “non-inferiority + cheaper” than SkillOpt’s “strictly higher score.” Useful when the north star is cost and we cannot lose safety.
- Do **not** import blindly: the four mechanisms are coding-agent token tricks, not Ask policy text. Terminal-Bench **lost 3 solves**. Search cost is huge (~500 envs); they admit no breadth/depth scaling law. Single-backend training (they say Opus triggers the tricks less). “RSI” here is harness search, not the model rewriting its own weights. 11 EdgeBench tasks were used for one-way freeze checks — still a leak risk if you blur that with the 40.

## Bottom Line
Search the **wrapper**, not the weights. Isolate lineages, freeze the bar, never let the report bench teach the next patch. You can cut tokens a lot and still lose a few solves — decide that trade before you search.
