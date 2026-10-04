# Metrics Summary

All active numbers in this file come from script outputs in `evals/latest/`, `evals/results/`, or `evals/results/cost_report.csv`. The old no-key LLM run was invalid because every row abstained due to missing credentials; that result directory has been removed and must not be used as evidence.

## Keyword Baseline

Source: `evals/latest/keyword_metrics_summary.csv` and the latest valid keyword run under `evals/results/`.

| Slice | Metric | Result | Note |
| --- | --- | ---: | --- |
| original12 | False negative rate, high/critical | 75.0% | 3 of 4 high/critical cases were not escalated; 95% CI 19.4%-99.4%. This slice was seen while tuning the keyword fallback. |
| original12 | False positive rate, normal criticism | 0.0% | 0 of 4 normal criticism cases were prompted/escalated; 95% CI 0.0%-60.2%. |
| original12 | Action accuracy | 66.7% | Predicted action equals gold policy action and does not abstain. |
| original12 | Macro F1 | 0.395 | Exact severity macro F1. |
| fresh | Fresh labelled cases | 0 | Waiting for human-reviewed `data/candidates_to_label.csv` merge in Phase C. |
| context | Strict / lenient movement accuracy | 80.0% / 80.0% | 5 context cases; one expected escalation missed. |

## Public Jigsaw Supplement

Source: latest valid keyword run `public_jigsaw_metrics.json`.

| Metric | Result | Note |
| --- | ---: | --- |
| Jigsaw mapped exact severity accuracy | 38.7% | Supplement only; labels are mechanically mapped from Jigsaw fields. |
| Jigsaw normal-reference FPR | 5.0% | 5 of 100 normal-reference rows were prompted/escalated. |
| Jigsaw high/critical FNR | 85.0% | Inflated by the mechanical mapping of severe toxic/profanity rows to high. |
| Jigsaw threat-flagged FNR | 50.0% | 7 of 14 rows with `jigsaw_threat=1` were not escalated. |
| Jigsaw profanity-only high upgrade rate | 7.7% | 3 of 39 high-mapped rows without threat were escalated. |

## Cost

Source: `evals/results/cost_report.csv`.

| Backend | Scenario | Token cost / 1,000 | Fallback cost / 1,000 | Total / 1,000 | Necessary review / 1,000 | Note |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| keyword | platform_assumed | USD 0.00 | USD 10.11 | USD 10.11 | 2.333 | Uses ASSUMED platform prevalence: normal 96%, medium 3%, severe 1%. |
| keyword | eval_observed_reference_only | USD 0.00 | USD 222.22 | USD 222.22 | 83.333 | Reference only; the 12-row set has an unrealistically high severe share. |

All prices, prevalence, review-time, wage, and harm-cost values are ASSUMED and must be verified before submission. No valid LLM quality or LLM cost result exists yet.
