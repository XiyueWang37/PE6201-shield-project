# Shield: AI-Assisted Harmful Content Intervention for Social Media Platforms

## 1. Problem and Product Goal

Online harassment is difficult to moderate because harm is often contextual. A single sentence may look harmless in isolation but become threatening when read after repeated unwanted contact, stalking cues, or earlier hostile messages. Existing moderation systems often intervene only after content is posted or reported, which means the user may already have experienced the harm. Shield is a prototype intervention system for social media and online community platforms. Its goal is to classify the harassment severity of a comment in context, then convert that severity into a transparent product action: allow, prompt the user to reconsider, or escalate to a human moderator.

The project is not designed to automatically punish users or replace moderators. The product value is earlier, lower-impact intervention. A reconsideration prompt can stop some harmful comments before publication, while severe or uncertain cases remain human-reviewed. This matters because the product must protect targets of harassment without turning every disagreement into a moderation event.

## 2. System Architecture

Shield separates model judgement from policy action. The input is a final comment and, when available, preceding thread context. A contextual severity classifier produces a structured output: severity label, short rationale, and confidence. A deterministic policy table then maps the label to an action. Normal and low-severity comments are allowed; medium-severity comments trigger a reconsideration prompt; high and critical cases are escalated to a moderator.

This split is deliberate. A foundation model is useful for language understanding, especially for context, ambiguity, sarcasm, and implicit threats. However, the final product action should not be hidden inside the model. A deterministic policy table makes the system auditable and adjustable. If the platform later decides that medium cases should be reviewed instead of prompted, the policy can change without retraining the classifier.

## 3. Data and Relabelling

My initial problem statement considered several public datasets, but I narrowed the final data strategy after intermediate feedback. The main work is not collecting many datasets; it is defining a severity taxonomy and relabelling examples into that taxonomy. For this submission, the repository includes a small prototype evaluation set with normal criticism, medium harassment, high or critical harassment, and context-sensitive cases. I also added a 300-row public Jigsaw supplementary sample, mechanically mapped into Shield labels, to make the repository less sparse. The core reported metrics still use the smaller inspectable eval set, while the intended full version is a 150-item hand-relabelled set.

I dropped OLID from the final plan because its tweet-ID re-fetching risk makes the project less reproducible. Instead, the final design focuses on a smaller, inspectable labelled set. This is a better match for the course objective because the labels and trade-offs can be explained, challenged, and improved. The normal-criticism slice is especially important because moderation products fail not only when they miss harm, but also when they interrupt legitimate disagreement too often.

## 4. Evaluation Design

The evaluation treats Shield as a product intervention, not only as a classifier. Reporting only false negatives on severe harassment would be incomplete because a lazy system could classify everything as high severity and achieve a perfect severe false-negative rate. That would be unusable in practice because ordinary users would be over-prompted or escalated for normal criticism.

For that reason, I report a pair of metrics. The first is false negative rate on high and critical harassment: how often severe cases are not escalated. The second is false positive rate on normal criticism: how often legitimate criticism is unnecessarily prompted or escalated. This pair captures the product trade-off between safety and user friction.

I also include a context-sensitivity evaluation. Each thread is designed so the final comment can be read alone, then read again with preceding context. The important question is whether the label moves when context changes the meaning. This test directly supports the central argument for using a foundation model rather than a simple keyword filter.

Finally, I include cost per 1,000 comments. At platform volume, a technically good intervention may still be impractical if its unit cost is too high. The repository currently reports this as an estimate below USD 0.10 per 1,000 short comments, with the note that it should be replaced by measured provider token usage in a production-grade run.

## 5. Results and Critique

The current repository includes a runnable local fallback classifier so the system can be demonstrated without an API key. On the small 12-case prototype evaluation set, overall accuracy is 66.7 percent. The false positive rate on normal criticism is 0 percent: none of the four normal criticism examples are prompted or escalated. This is good for user friction, but it also reveals a weakness. The false negative rate on high and critical cases is 75 percent: three of four high or critical examples are not escalated by the local fallback.

This poor severe-harm result is useful because it shows why the fallback is not the final classifier. It catches explicit hostile terms but misses implicit threats such as location-based intimidation. In product terms, that is the dangerous failure mode: the system looks calm while quietly under-reacting to severe harassment. The result supports the architecture choice rather than invalidating it. Shield should use a contextual foundation model for severity classification, then use the deterministic policy layer for action selection.

The context evaluation contains five designed thread cases. Three require escalation when context is included, and two should remain unchanged. This evaluation is small, but it demonstrates the kind of test the full system needs: the same final comment should not always receive the same label if the surrounding thread changes its meaning.

## 6. Responsible Use and Limitations

Shield should not make high-impact enforcement decisions alone. High and critical cases should be routed to human moderators, and uncertain cases should be logged for review. The biggest risk is silent failure: a severe case is labelled normal or medium, no one notices, and the target user receives no protection. False positives are also harmful because repeated unnecessary prompts can suppress legitimate criticism and make users distrust the platform.

The current evaluation is small and English-only. It does not adequately test multilingual abuse, coded language, demographic bias, or adversarial spelling. The severity taxonomy also needs further validation with moderator input. A production version would require a larger labelled dataset, ongoing drift monitoring, bias slices, appeal workflows, and clear privacy rules for sending user text to an external model provider.

## 7. Future Path

The next version should replace the local fallback with a measured foundation-model classifier and run the full 150-item hand-relabelled evaluation set. I would then report the same metric pair: severe false-negative rate and normal-criticism false-positive rate, plus cost per 1,000 comments. I would also expand the context test because it is the strongest evidence that Shield is doing contextual moderation rather than keyword matching.

The long-term product path is not full automation. It is a human-in-the-loop workflow where AI handles early triage and structured explanation, while moderators retain authority over severe, uncertain, and appealable cases. That makes Shield useful as a safety intervention while keeping the most consequential decisions accountable.
