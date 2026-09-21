# Scaling Articulated Rationales for MLLM-based Recommendation (Live / Rec, Kuaishou)

## Paper Link
https://arxiv.org/abs/2609.17639

## Kuaishou Live logic (read this first)

You do not need the app. **Live** is a vertical feed of people streaming (chat, dance, selling). The ranker mostly sees **what** you did: watch, skip, gift, tap Dislike. Same skip can mean “selling too hard” or “audio is noisy.” That *why* is missing.

Sometimes, after ~10 seconds of watching, a popup asks: like or dislike this stream? Then “why?” That sentence is an **articulated user rationale (AUR)**. Almost nobody writes one (coverage $<1\%$). When they do, 82% of answers are $\le 10$ Chinese characters. So you cannot train ranking on raw AURs for 10M streamers.

SARA’s move: clean the rare sentences, teach a 7B model to write **author-level** like/dislike reasons from the video, then stuff those texts into the ranker. The generated “why” is shared by **every viewer of that streamer**. It is not “why *you* liked it.”

## One-Line Summary
Turn sparse “why I liked/skipped this live” sentences into a judged HQ set, clone them onto 10M streamers with SFT + judge-ranked DPO, and use +/− texts as ranking features — clicks stay *what*, these texts are the *why*.

## Core Problem
Behavior is cheap and ambiguous. Native AURs are sparse, short, and messy. A general MLLM asked to explain a skip will **invent** a plausible why (post-hoc rationalization). Need a pipeline that collects, filters, scales, and actually consumes the reasons.

## Terminology

| Symbol | Plain meaning |
|---|---|
| AUR | User’s own like/dislike + one-sentence why, from a questionnaire. |
| SARA-HQ | Curated AURs: 187,532 rows, 86,564 authors, $G>2$. |
| $p \in \{+,-\}$ | Polarity the model is asked to write (like vs dislike). |
| $\mathcal{X}$ | Video + title + comments + ASR + instruction. |
| SARA-7B | Qwen2.5-VL-7B after SFT then QR-DPO. |
| QR-DPO | Sample $K$ rationales from SFT; Agent Judge ranks; best vs worst $\to$ DPO pair. |
| $G \in \{1,2,3,4\}$ | Holistic quality. Incentive / keep if $G>2$. Not the mean of the six dims. |
| $R_a^+$, $R_a^-$ | Generated +/− rationale for **author** $a$, not for a user. |
| SID | 3-level code of a rationale embedding so similar *reasons* share IDs. |

Six judge dims: coherence, relevance, specificity, safety, polarity consistency, grounding. **Non-compensatory:** fluent garbage that contradicts $p$ or is ungrounded still fails holistic $G$.

## Method

```text
popup (5% of sessions, after 10s watch)
  → like/dislike + why
  → online 0.5B judge: G>2 gets a small reward
  → offline Agent Judge (6 specialists + Senior Review) keeps HQ
SFT on HQ: given stream + polarity, copy the cleaned why
QR-DPO: SFT samples K, Agent ranks, DPO on (best, worst)
SARA-7B writes R_a^+ and R_a^- for all 10M authors
ranker: + texts as embeddings (match user↔author reason)
        − texts as SIDs on Hate history (transfer “hard sell” to unseen streamers)
```

SFT is next-token on rationale tokens. QR-DPO is standard DPO; the **label** of which sample is better is the Agent Judge, not a click.

Daily refresh, $>30$ days in production.

## Concrete Example
You skip a livestream. Dislike bit is 1. No why.

A rare questionnaire: “Negative — they kept pushing WeChat to buy a course.” That is an AUR. Agent Judge: specific, polarity matches, grounded in the pitch $\to$ HQ.

SARA-7B, asked for **negative** on a *similar* finance streamer with no questionnaire: “exaggerated promises, DM to buy, noisy pitch.” That $R_a^-$ becomes a SID. Next time you Hate one hard-sell streamer, the ranker can down-rank **other** authors with the same SID, not only the same author ID.

Do **not** read $R_a^-$ as *your* reason. It is an author-side proxy cloned from people who filled the form.

Ask analog: a few users write “this pin is NSFW, not fashion.” Don’t wait for every pin. Judge-filter those sentences, generate author/pin-level +/− blurbs, use them as features — and do not treat the blurb as that user’s label.

## Results
Collection (Feb–Aug 2026): 1.92M raw AURs $\to$ 187k HQ (9.8% yield). Negatives pass the bar more often (defect-focused); positives are full of generic praise.

SARA-7B vs Gemini-3.1-Pro / Qwen3-VL-8B on 5k **author-disjoint** eval (Agent Judge 1–4; BGE-Sim to original AUR):

```text
                 holistic   BGE-Sim   specificity
Gemini           2.51       0.70      2.92
Qwen3-VL-8B      2.37       0.69      2.67
SARA-7B SFT      3.15       0.82      3.07
SARA-7B DPO      3.33       0.82      3.32
```

Judge vs human MAE, holistic: zero-shot 0.58, online LLM 0.35, Agent 0.20 (inter-expert 0.10). Senior Review is what drops holistic MAE 0.29 $\to$ 0.20.

SARA-Ranker, 1% A/B, $>30$ days:

```text
+ embeddings:  Click +0.34%  watch time +0.99%  follow +0.62%
− SIDs:        Hate −8.16%   Report −0.44%     LT-7 +0.03%
```

## Relation to Our Work
- **Directly useful** for label quality / LLM-as-judge. Sibling to Netflix RART (human *fail* reasons on explanations) and Spotify QRI (debiased *behavior* card). SARA’s gold is a user-written **why** with a polarity bit; the judge’s job is filter + DPO ranking, not the live ranker.
- Rubric is non-compensatory (fluency cannot rescue a polarity fail). That is the right shape for a gate. Online 0.5B is only for “pay the user”; HQ and DPO pairs come from the Agent + Senior Review. Same split we want: cheap live vs expensive gold.
- QR-DPO is self-play ranked by a **trained** judge, not by clicks. Compare to `training.py`: here the editor is DPO and the critic is the Agent Judge. Do not swap in raw engagement as $y^+$ / $y^-$.
- Do **not** import blindly: $R_a$ is **author-global**, so it can wash out user-specific why; 9.8% HQ yield means the judge throws away most AURs; BGE-Sim to the original form is not “true intent”; Hate −8% is Kuaishou Live, not a safety classifier. Generated why can still be a fluent lie — they only claim it is closer to questionnaire HQ than Gemini is.

## Bottom Line
Clicks say what happened. A rare judged sentence says why. Clone that sentence onto the long tail with a polarity-conditioned MLLM, then rank with +/− text — and never pretend the clone is *this* user’s reason.
