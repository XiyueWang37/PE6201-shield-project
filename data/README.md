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

## Files

- `relabelled_150_template.csv`: template for the 150 hand-relabelled items.

Do not include private platform data or API keys in this folder.
