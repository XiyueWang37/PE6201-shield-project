# Data Explanation

The final project avoids treating dataset collection as the main contribution. The core evaluated set remains small and inspectable, while a larger public sample is included as supplementary evidence.

## Files

- `relabelled_eval_set.csv`: small hand-labelled prototype evaluation set used for the core reported metrics. The intended full version is 150 human-reviewed items.
- `public_jigsaw_sample_300.csv`: supplementary public Jigsaw sample with 100 normal, 100 medium, 50 high, and 50 critical mapped examples.
- `candidates_to_label.csv`: AI-drafted candidate rows for human review. The `shield_label` column is intentionally blank; `proposed_label` is only a suggestion.

## Jigsaw Supplement Mapping

The public Jigsaw sample comes from the Jigsaw Toxic Comment Classification Challenge through the `preethi16102005/Jigsaw-Toxic-Comments` Hugging Face mirror. It contains long Wikipedia talk-page comments, so its distribution differs from short social media comments.

The mapping used in `public_jigsaw_sample_300.csv` is visible in the `jigsaw_*` columns and `mapping_notes`:

- all Jigsaw toxicity labels are `0` -> `normal`
- `toxic`, `insult`, or `obscene` without `severe_toxic`, `threat`, or `identity_hate` -> `medium`
- `severe_toxic` or `threat` without `identity_hate` -> `high`
- `identity_hate` -> `critical`

These mapped labels are not human severity judgements. They are a mechanical bridge from Jigsaw's label schema into Shield's taxonomy and should be reported separately from the core hand-labelled eval.

In the current 300-row supplement, the mechanically mapped `high` bucket contains 50 rows. Only 11 of those rows have `jigsaw_threat=1`; the remaining 39 are high because of `severe_toxic` without an explicit threat flag. The evaluation runner therefore reports two extra slices: `jigsaw_threat_flagged` FNR and `jigsaw_profanity_only_high` upgrade rate. This prevents the coarse high bucket from overstating evidence about true threat detection.

## Human Review Plan

The file `candidates_to_label.csv` contains AI-drafted examples covering normal criticism, non-targeted profanity, sarcasm, implicit threats, location or routine intimidation, and multi-comment context cases. A human reviewer should fill `shield_label`, then any accepted rows can be merged into a larger core set with `labeller=human_reviewed`.

Do not include private platform data or API keys in this folder.
