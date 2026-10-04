# Data Explanation

The final project treats data review as part of the build, not as a side detail. The active core evaluation file is `core_eval_set.csv`, which combines the original 12 inspected examples with 90 user-confirmed fresh single-comment candidates.

## Files

- `relabelled_eval_set.csv`: original 12-row prototype set. These rows are marked `tuned_on=true` in `core_eval_set.csv` because the keyword fallback was developed around them.
- `candidates_to_label.csv`: 102 AI-drafted candidates confirmed by the user from the review draft. The confirmed distribution is normal 40, low 8, medium 13, high 25, critical 16. Of these, 90 are single-comment rows and 12 are thread rows.
- `candidates_review_draft.csv`: review helper file with suggested labels and `review_status=needs_user_confirmation` before confirmation.
- `core_eval_set.csv`: derived file used by `evals/run_eval.py`; it contains original12 plus the 90 fresh single rows.
- `split_ids.csv`: fixed seed 6201, stratified fresh dev/test split for prompt tuning.
- `public_jigsaw_sample_300.csv`: supplementary public Jigsaw sample with 100 normal, 100 medium, 50 high, and 50 critical mapped examples.

## Human Review Caveat

The fresh labels were user-confirmed from an AI-drafted candidate sheet. This is better than unreviewed generated labels, but it is still a limitation: there is one reviewer, no adjudication, and the examples were drafted rather than sampled from a production platform. The report treats this as a prototype evaluation, not deployment-grade ground truth.

## Jigsaw Supplement Mapping

The public Jigsaw sample comes from the Jigsaw Toxic Comment Classification Challenge through the `preethi16102005/Jigsaw-Toxic-Comments` Hugging Face mirror. It contains long Wikipedia talk-page comments, so its distribution differs from short social media comments.

The mapping used in `public_jigsaw_sample_300.csv` is visible in the `jigsaw_*` columns and `mapping_notes`:

- all Jigsaw toxicity labels are `0` -> `normal`
- `toxic`, `insult`, or `obscene` without `severe_toxic`, `threat`, or `identity_hate` -> `medium`
- `severe_toxic` or `threat` without `identity_hate` -> `high`
- `identity_hate` -> `critical`

These mapped labels are not human severity judgements. They are a mechanical bridge from Jigsaw's label schema into Shield's taxonomy and should be reported separately from the core fresh eval.

In the 300-row supplement, the mechanically mapped `high` bucket contains 50 rows. Only 11 of those rows have `jigsaw_threat=1`; the remaining 39 are high because of `severe_toxic` without an explicit threat flag. The evaluation runner therefore reports `jigsaw_threat_flagged` FNR and `jigsaw_profanity_only_high` upgrade rate. This prevents the coarse high bucket from overstating evidence about true threat detection.

Do not include private platform data or API keys in this folder.
