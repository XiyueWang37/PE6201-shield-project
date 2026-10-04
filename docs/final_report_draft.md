# Shield: AI-Assisted Harmful Content Intervention for Social Media Platforms

## 1. Product Goal

Shield is a prototype for social media Trust and Safety teams. It classifies the harassment severity of a comment, optionally using preceding thread context, then maps that label into a deterministic action: allow, prompt the user to reconsider, or escalate to a moderator. The change versus today's reactive moderation is timing and consistency. Instead of waiting for a target to report a harmful comment, Shield can intervene earlier while still leaving severe or uncertain cases to humans.

The product goal is not automatic punishment. A system that escalates everything can score a perfect false-negative rate, but it would also over-prompt normal criticism and overload moderators. I therefore evaluate Shield as a product intervention: it must reduce missed high-risk comments without making ordinary disagreement feel unsafe to post.

## 2. System Design

The architecture separates judgement from action. The classifier returns severity, rationale, confidence, token usage, and abstention status. The deterministic policy table in `src/policy.py` then maps normal and low to `allow`, medium to `prompt_reconsider`, and high or critical to `escalate_to_moderator`. This keeps the action layer auditable even when the classifier backend changes.

The repository contains two backends. The keyword fallback is a transparent baseline, not a deployable model. The LLM backend uses an OpenAI-compatible JSON prompt, cache replay, usage accounting, and fail-fast behavior when the API key or cache is missing. API keys are never stored. The final submitted prompt is `prompt_v2`, with `prompt_v1` retained for the tuning comparison.

## 3. Data and Evaluation

The active core evaluation file has 102 rows: the original 12 inspected examples plus 90 fresh single-comment candidates confirmed from a review draft. The original 12 are marked `tuned_on=true` because the keyword baseline was developed around them; the headline comparison therefore uses the fresh slice. The fresh slice contains 35 normal criticism rows and 35 high or critical rows. I also expanded the context evaluation to 17 cases.

The candidate set is useful, but it is not perfect ground truth. It was AI-drafted and confirmed by one reviewer, so it may contain same-family optimism and single-labeller bias. I changed 0 labels from the draft suggestions, which is transparent evidence that the review pass confirmed rather than substantially revised the draft. The 300-row Jigsaw supplement is reported separately because its labels are mechanically mapped from toxicity fields. Its high bucket is especially noisy: only 11 of 50 high-mapped rows have the Jigsaw threat flag, while 39 are severe-toxic or profanity-only rows. That is why I report Jigsaw threat-flagged FNR separately from profanity-only high escalation rate.

The evaluation reports high/critical false-negative rate, normal-criticism false-positive rate, action accuracy, exact severity accuracy, macro F1, abstention, context movement, lazy all-high baseline, and Clopper-Pearson confidence intervals.

## 4. Results and Critique

On the fresh slice, the keyword baseline fails the safety objective. It has 94.3% high/critical FNR, 0.0% normal FPR, 44.4% exact accuracy, 51.1% action accuracy, and macro F1 of 0.224. Its low FPR is useful, but it is mostly achieved by allowing too much. It misses many implicit threats and location cues, such as workplace, commute, or waiting references.

LLM prompt_v2 is substantially better on the same fresh slice: 5.7% high/critical FNR, 0.0% normal FPR, 74.4% exact accuracy, 88.9% action accuracy, and macro F1 of 0.617. The FNR confidence interval is still wide, 0.7% to 19.2%, so this is promising but not deployment proof. On context movement, keyword reaches 58.8% strict and lenient accuracy, while LLM v2 reaches 82.4% strict and 88.2% lenient. The LLM still missed two expected movement cases, including cases where it already labelled the final comment high without context, so the movement metric did not register an escalation.

The lazy all-high baseline is the warning sign. It gets 0.0% high/critical FNR but 100.0% normal FPR. That would be a terrible product because every normal criticism would create friction. Shield must be judged by paired safety and friction metrics.

On Jigsaw, LLM v2 improves the threat-flagged subset FNR to 21.4% versus keyword's 50.0%, but the overall mapped high/critical FNR remains 67.0%. I treat that as supplementary evidence only because the mapping is mechanical and the data domain differs from short social media threads.

## 5. Prompt Tuning

Prompt tuning was limited to one change. I split the fresh rows once with seed 6201, stratified by label. Before changing the prompt, I inspected only dev failures. Prompt v1 often labelled direct insults as low and implicit location or regret cues below high. The v2 hypothesis was that explicit boundary calibration would reduce missed high-risk and medium cases without increasing normal criticism FPR.

The held-out test result supported the hypothesis. Action accuracy improved from 78.3% to 87.0%, high/critical FNR improved from 22.2% to 5.6%, and normal FPR stayed 0.0%. Because v2 improved the held-out split, I use v2 as the submitted prompt.

## 6. Cost and Class 5 Coverage

The cost model uses the course formula: cost per task equals token cost plus `(1 - p) * fallback_cost`, where `p` is correct policy action with no abstention. Correct escalation of high-risk comments is necessary review load, not failure. Under ASSUMED platform prevalence, normal 96%, medium 3%, high 0.7%, critical 0.3%, keyword costs USD 18.58 per 1,000 comments. LLM v2 costs USD 11.70 per 1,000, including USD 0.064674 token cost and USD 11.64 expected fallback cost. These prices, wages, prevalence values, monthly volume, and the missed-harm cost of 0 are all ASSUMED and must be verified.

No frontier model was measured. The break-even calculation says a frontier tier would need p* = 0.985403 under ASSUMED frontier token prices and cheap measured token volume, compared with the cheap model's measured p = 0.982542. I do not claim a frontier result.

## 7. Limitations and Future Path

The main difficulty was making the project auditable: replacing hand-written claims with scripts, cached outputs, fail-fast LLM runs, confidence intervals, prompt-version tracking, and cost tests. The rough edges remain real. The data is small, partly AI-drafted, and single-reviewed. The keyword baseline has substring and test-tuning weaknesses. The LLM still misses some implicit offline threats, for example "I am going to be outside after the meeting." Future work should add independent annotators, adversarial spellings, identity-abuse slices, calibrated uncertainty, appeal handling, and a real moderator workflow. Shield is therefore a strong prototype, not a ready moderation authority.
