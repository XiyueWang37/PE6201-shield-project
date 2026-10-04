# Data Explanation

The final project should avoid treating dataset collection as the main contribution. Based on intermediate feedback, the data strategy is narrowed to a smaller hand-relabelled evaluation set.

## Final Data Strategy

- Use around 150 hand-relabelled comments as the core evaluation set.
- Label each item into Shield's severity taxonomy: `normal`, `low`, `medium`, `high`, or `critical`.
- Include a normal-criticism slice so false positives and over-prompting can be measured.
- Include high/critical cases so severe false negatives can be measured.
- Use a separate context-sensitivity set of short threads where the final comment is tested alone and with preceding context.

## Dataset Scope Decision

The original project statement considered several public datasets. The final submission should emphasize relabelling quality rather than the number of source datasets. OLID is dropped because tweet-ID re-fetching introduces avoidable access and reproducibility risk.

## Public Supplement

To make the repository less sparse while keeping the data strategy simple, I added a 300-row supplementary sample from the public Jigsaw Toxic Comment Classification Challenge dataset. This sample is mechanically mapped into Shield labels from the original Jigsaw labels, so it should be treated as public supplementary testing data, not as hand-relabelled ground truth.

Source: Jigsaw Toxic Comment Classification Challenge, accessed through the `preethi16102005/Jigsaw-Toxic-Comments` Hugging Face mirror. The dataset contains original comment text and labels such as `toxic`, `severe_toxic`, `threat`, `insult`, and `identity_hate`.

## Files

- `relabelled_eval_set.csv`: hand-labelled prototype evaluation set used for the reported metrics. The intended full version is 150 relabelled items.
- `public_jigsaw_sample_300.csv`: supplementary public Jigsaw sample with 100 normal, 100 medium, 50 high, and 50 critical mapped examples.

Do not include private platform data or API keys in this folder.
