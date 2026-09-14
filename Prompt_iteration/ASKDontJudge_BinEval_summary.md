# Ask, Don't Judge: Binary Questions for Interpretable LLM Evaluation and Self-Improvement

## Paper Link

https://arxiv.org/abs/2606.27226

## One-Line Summary
BINEVAL evaluates LLM outputs by decomposing criteria into atomic yes/no questions, aggregating those verdicts into interpretable multi-dimensional scores, and using question-level disagreements/failures to iteratively improve evaluator or generator prompts.

## Core Problem
LLM evaluation is a bottleneck:

- human eval is expensive,
- lexical metrics miss semantic/factual quality,
- holistic LLM judges give opaque scores that are hard to debug,
- a single scalar does not tell whether failure is factuality, relevance, fluency, etc.

The premise: ask many small checkable questions instead of one broad judgment.

## Terminology

| Symbol | Meaning |
|---|---|
| $T$ | Task prompt being evaluated / generated. |
| $R = \{r_1,\ldots,r_K\}$ | Requirements extracted from $T$. |
| $Q_d$ | Atomic yes/no questions for quality dimension $d$. |
| $Q = \bigcup_d Q_d$ | Full question set. |
| $f_E(x,y,q_i) \in \{0,1\}$ | Evaluator answer to question $q_i$ on input $x$ and output $y$. |
| $S_d(x,y)$ | Mean of answers in dimension $d$. |
| $S(x,y)$ | Mean over all $N$ questions. Both scores live in $[0,1]$. |

## Method
Three components:

```text
1. Binary question generation
2. Binary evaluation + scoring
3. Iterative prompt optimization
```

### 1. Question generation
Given task prompt `T`, a meta-prompt does:

```text
Step 1: summarize T into requirements R = {r1, ..., rK}
Step 2: decompose each requirement into atomic yes/no questions
```

Questions are grouped by dimensions (e.g., coherence, consistency, fluency, relevance): $Q = \bigcup_d Q_d$.

### 2. Evaluation and scoring
For each question $q_i$, the evaluator returns $f_E(x,y,q_i) \in \{0,1\}$ plus a short explanation.

$$
S_d(x,y) = \frac{1}{|Q_d|}\sum_{q \in Q_d} f_E(x,y,q),
\qquad
S(x,y) = \frac{1}{N}\sum_{q \in Q} f_E(x,y,q).
$$

### 3. Prompt optimization from binary feedback

**Cross-model evaluator update**

```text
source evaluator vs target evaluator
? find disagreeing binary questions
? note-taker extracts lessons
? updater patches target evaluator prompt
```

**Self update for generation**

```text
generate with current prompt
? collect failed questions + explanations
? extract lessons
? update generation prompt
```

Stop when disagreement/error is small enough or iteration budget ends.

## Concrete Example
Summarization evaluation for consistency.

Instead of:

```text
Rate consistency 1 to 5
```

BINEVAL asks atomic checks such as:

```text
Q1: Does every named entity in the summary appear in the source?
Q2: Are all numerical claims supported by the source?
Q3: Does the summary invent causes/events not in the source?
Q4: Are temporal relations consistent with the source?
```

Suppose answers:

```text
yes, yes, no, yes
```

Then:

$S_{\mathrm{consistency}} = 0.75$

with an explanation pointing to the invented causal claim. That failure can also become a lesson for prompt update:

```text
Require that causal links be explicitly stated in the source before inclusion.
```

## Results
**SummEval** (Spearman / Kendall averages):

```text
BINEVAL (Claude): 0.563 / 0.491   best overall
G-Eval (GPT-4):   0.514 / 0.418
UniEval (T5):     0.474 / 0.377
```

Especially strong on consistency (`0.655 / 0.615`). Relevance remains harder for binary decomposition; G-Eval (GPT-4) still wins there.

**Topical-Chat**

```text
BINEVAL (Claude) best average Spearman ? 0.632
```

**QAGS** (factual consistency / hallucination)

```text
BINEVAL (Claude) best average Spearman ? 0.620
```

Decomposition helps most on hallucination-prone data.

**Prompt update**

- SummEval evaluator update: average Spearman `+0.075` (self) / `+0.070` (cross-model).
- Gains mostly in first 1-2 iterations; later iterations can degrade via competing instructions.
- Relevance does not improve under either update mode (over-decomposition makes evaluator too severe).
- IFBench generation update: modest peak `+3.4pp`, then collapse; format/sentence constraints improve, count/ratio/compute constraints do not.

Key takeaway from optimization experiments:

```text
Binary feedback helps when the model already has the capability
but needs clearer guidance.
It cannot create missing computational skills and may cause prompt bloat.
```

## Relation to Our Research
**Directly useful for evaluator / policy diagnosis; adjacent to our optimizer loop.**

Closest mapping:

| BINEVAL idea | Our research |
|---|---|
| Atomic binary questions | Decompose policy criteria into checkable clauses |
| Question-level explanations | Failure summaries for clustering / hypothesis generation |
| Disagreement-driven lessons | Cross-judge / gold-vs-LLM disagreement signals |
| Iterative evaluator prompt update | Rubric/policy optimization under gates |
| Multi-dimensional scores | Separate FPR/FNR / DQ dimensions instead of one F1 |

Useful takeaways:

1. Prefer ask don't judge for Trust & Safety / labeling audits: many atomic checks beat one holistic LLM score.  
2. Use failed questions as diagnosis units before rewriting policy (`VISTA`-like / clustering-like).  
3. Cross-model disagreement on binary checks is a strong lesson signal for rubric alignment.  
4. Cap update iterations; late lessons can overfit and bloat the prompt.

What not to import blindly:

- Not every quality (e.g., 'relevance') decomposes cleanly into binaries.
- More questions ? better alignment; over-decomposition can make judges too harsh.
- Evaluation cost rises with number of questions.
- Self-update can collapse after a few iterations without strong acceptance gates.

Relative to papers we already reviewed:

- Complements Clustering Prompt Opt: binary failures are natural clusterable units.
- Complements VISTA: questions ? explicit hypotheses / root-cause checks.
- Complements SkillOpt: lesson patches should be bounded and gated.
- Different from HUMBR: BINEVAL decomposes criteria; HUMBR selects among candidate answers.

## Bottom Line
BINEVAL's core lesson is: evaluate with many small yes/no questions, not one opaque judgment. That yields better discrimination, better diagnostics, and a cleaner feedback signal for prompt/rubric improvement especially for factual consistency while requiring care against over-decomposition and prompt bloat.
