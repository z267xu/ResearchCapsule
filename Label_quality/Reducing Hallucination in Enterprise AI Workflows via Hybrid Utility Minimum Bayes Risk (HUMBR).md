# Reducing Hallucination in Enterprise AI Workflows via Hybrid Utility Minimum Bayes Risk (HUMBR)

## Paper Link

https://arxiv.org/abs/2604.11141

## Core Idea

This paper proposes **Hybrid Utility Minimum Bayes Risk (HUMBR)**, a reference-free method for reducing hallucination in high-stakes LLM workflows.

The key insight is:

> Individual LLMs may hallucinate, but they often hallucinate differently. True information tends to form a consensus cluster, while hallucinations tend to appear as isolated outliers.

Instead of trusting one model output, HUMBR generates multiple candidate outputs from different models or decoding settings, computes pairwise agreement among them, and selects the candidate closest to the consensus center. If the consensus is weak, the system abstains rather than forcing an answer.

## Terminology

| Symbol | Meaning |
|---|---|
| $x$ | Input (prompt / document / image+policy). |
| $C = \{c_1,\ldots,c_N\}$ | Candidate outputs from $K$ models $\times$ $M$ samples. |
| $U(c_i,c_j)$ | Pairwise utility (agreement) between two candidates. |
| $\alpha$ | Weight on semantic vs lexical similarity. |
| $\mathrm{Score}(c_j)$ | Mean agreement of $c_j$ with all candidates (consensus). |
| $c^*$ | Selected candidate (closest to the consensus center). |
| $\tau$ | Abstain threshold on $\max_j \mathrm{Score}(c_j)$. |
| $\rho$ | Intra-model correlation of samples from the same model. |
| $N_{\mathrm{eff}}$ | Effective sample size after that correlation. |

## Method

Given an input $x$, generate a candidate set $C = \{c_1,\ldots,c_N\}$. Pairwise utility:

$$
U(c_i, c_j) = \alpha \cdot \mathrm{semantic}(c_i,c_j) + (1-\alpha) \cdot \mathrm{lexical}(c_i,c_j).
$$

Semantic similarity is embedding cosine; lexical is ROUGE-L. Consensus score and selection:

$$
\mathrm{Score}(c_j) = \frac{1}{N}\sum_i U(c_i,c_j),
\qquad
c^* = \arg\max_j \mathrm{Score}(c_j).
$$

Abstain if the best consensus is weak:

$$
\text{if } \max_j \mathrm{Score}(c_j) \ge \tau \text{ then return } c^* \text{ else abstain / human review.}
$$

This is different from asking another LLM to summarize all answers. HUMBR selects one of the original candidates, which reduces the risk that a summarizer introduces a new hallucination.

## Theoretical Framing

The paper frames hallucination mitigation as a **Minimum Bayes Risk** problem. Instead of choosing the most likely answer under one model, HUMBR chooses the answer with the lowest expected disagreement relative to the candidate distribution.

The paper also models correlation among model outputs. With $K$ models and $M$ samples per model, $N = KM$, but same-model samples are correlated:

$$
N_{\mathrm{eff}} = \frac{KM}{1 + (M-1)\rho}.
$$

This gives an important operational lesson:

> Adding more samples from the same model has diminishing returns when correlation is high. Diversity across models and decoding settings matters more than just increasing sample count.

## Reported Results

On TruthfulQA:

```text
Greedy decoding:              69.5%
Universal Self-Consistency:   76.5%
HUMBR:                        80.3%
Oracle upper bound:           81.5%
```

On LegalBench:

```text
Greedy balanced accuracy:     34.0%
USC balanced accuracy:        36.5%
HUMBR balanced accuracy:      50.2%
```

In Meta's internal regulatory workflow:

```text
HUMBR vs human expert drafts: 81.0% win rate
HUMBR vs USC:                 89.5% win rate
```

The paper also reports that HUMBR reduces certain critical recall failures, such as missing key sections of source text, but may increase citation/style issues because it can include implied or insufficiently cited details.

## Example: Applying HUMBR to Our Image + Prompt Judge Workflow

In our use case, each sample may contain:

```text
image + policy/judging prompt
```

We send the same sample to 5 LLM judges. Each judge returns a structured output:

```json
{
  "label": "violation",
  "confidence": 0.87,
  "reason": "The image shows explicit self-harm encouragement.",
  "evidence": ["visible injury", "instructional text", "weapon near wrist"],
  "policy_node": "self_harm_instruction"
}
```

Suppose the 5 outputs are:

```text
C1: violation, self-harm instruction, confidence 0.91
C2: violation, self-harm encouragement, confidence 0.88
C3: violation, self-harm method detail, confidence 0.84
C4: non-violation, medical education, confidence 0.62
C5: violation, self-harm instruction, confidence 0.89
```

A simple majority vote would return `violation`. HUMBR-style consensus goes further: it checks whether the models agree not only on the label, but also on the reason, evidence, and policy node.

A practical pairwise utility for our workflow could be:

$$
U(C_i,C_j)
= 0.5 \cdot \mathbf{1}[\mathrm{label}_i=\mathrm{label}_j]
+ 0.2 \cdot \cos(\mathrm{reason}_i,\mathrm{reason}_j)
+ 0.2 \cdot \mathrm{Jaccard}(\mathrm{evidence}_i,\mathrm{evidence}_j)
+ 0.1 \cdot \mathbf{1}[\mathrm{policy}_i=\mathrm{policy}_j].
$$

Then $\mathrm{Score}(C_j) = \frac{1}{N}\sum_i U(C_i,C_j)$ and $C^* = \arg\max_j \mathrm{Score}(C_j)$.

In the example above, `C1`, `C2`, `C3`, and `C5` form a strong consensus cluster. `C4` is an outlier. The system would accept the consensus label:

```text
selected label = violation
selected rationale = the most central candidate's rationale
action = accept label
```

## Abstention Example

If the 5 judges produce:

```text
C1: violation, self-harm
C2: non-violation, medical education
C3: violation, graphic violence
C4: non-violation, news context
C5: unclear, low confidence
```

then there is no stable consensus. Even if 3 models say `violation`, the rationales point to different policy concepts. In that case:

$$
\max_j \mathrm{Score}(C_j) < \tau
$$

The system should not trust the label:

```text
action = abstain / send to human review / mark as ambiguous
```

## How This Helps Our Training Loop

HUMBR can be used as a label-quality layer before policy optimization.

Suggested actions:

```text
high consensus + high confidence:
    use as reliable training/evaluation signal

low consensus:
    exclude from policy-update examples
    send to human review

high LLM-consensus disagreement with golden label:
    mark the golden label as suspicious
    send to human re-adjudication
```

This is especially useful for the label-suspicious problem we discussed earlier. If a sample repeatedly appears as high-gradient and multiple independent LLM judges agree against the golden label, then the issue may not be the policy. The issue may be the golden label.

## Practical Caveats

HUMBR is not free. It increases inference cost because each sample is sent to multiple LLMs. For our workflow, this may only be affordable for:

- high-gradient examples,
- suspected label-noise examples,
- validation/gate examples,
- high-risk policy categories,
- samples near the decision boundary.

HUMBR also depends on diversity. If all 5 LLM judges share the same bias, they can form a false consensus. To reduce this risk, we should use:

- different model families where possible,
- different prompt phrasings,
- temperature or decoding diversity,
- historical reliability weights per judge,
- human review for low-consensus or high-impact cases.

## Bottom Line

HUMBR is useful for our workflow as a **consensus-based reliability filter**.

The practical takeaway is:

> Use multiple LLM judges not only to vote on the final label, but to measure whether the label, rationale, evidence, and policy-node attribution are all aligned. Accept high-consensus cases, abstain on low-consensus cases, and use repeated high-consensus disagreement with golden labels as a signal for human re-adjudication.
