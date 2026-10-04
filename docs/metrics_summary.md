# Metrics Summary

All active numbers come from script outputs in `evals/latest/`, `evals/results/`, and `evals/results/cost_report.csv`. The old no-key LLM run was invalidated and is not used.

## Core Evaluation

Headline results use the fresh human-reviewed candidate slice. The original12 slice remains reported because it was seen while developing the keyword fallback.

| Backend | Slice | FNR high/critical | FPR normal criticism | Action accuracy | Severity accuracy | Macro F1 | Abstention |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| keyword | original12 | 75.0% | 0.0% | 66.7% | 66.7% | 0.395 | 0.0% |
| keyword | fresh | 94.3% | 0.0% | 51.1% | 44.4% | 0.224 | 0.0% |
| keyword | combined | 92.3% | 0.0% | 52.9% | 47.1% | 0.261 | 0.0% |
| LLM prompt_v2 | original12 | 0.0% | 0.0% | 83.3% | 75.0% | 0.483 | 0.0% |
| LLM prompt_v2 | fresh | 5.7% | 0.0% | 88.9% | 74.4% | 0.617 | 0.0% |
| LLM prompt_v2 | combined | 5.1% | 0.0% | 88.2% | 74.5% | 0.616 | 0.0% |

Fresh confidence intervals: keyword FNR 80.8%-99.3%, keyword FPR 0.0%-10.0%; LLM FNR 0.7%-19.2%, LLM FPR 0.0%-10.0%.

## Context Movement

| Backend | Context n | Strict accuracy | Lenient accuracy | Missed expected escalations |
| --- | ---: | ---: | ---: | ---: |
| keyword | 17 | 58.8% | 58.8% | 7 |
| LLM prompt_v2 | 17 | 82.4% | 88.2% | 2 |

Keyword missed examples include `See you soon.` after stalking context and `I will wait.` after parking-location context. LLM v2 still missed `I will see you again.` and `I will wait.` as movement cases because it already labelled the final comment high without context.

## Lazy Baseline

The all-high baseline gets 0.0% FNR on high/critical cases but 100.0% normal-criticism FPR. This is a product failure even though the safety recall metric looks perfect.

## Public Jigsaw Supplement

| Backend | Jigsaw normal-reference FPR | Jigsaw high/critical FNR | Threat-flagged FNR | Profanity-only high upgrade rate |
| --- | ---: | ---: | ---: | ---: |
| keyword | 5.0% | 85.0% | 50.0% | 7.7% |
| LLM prompt_v2 | 3.0% | 67.0% | 21.4% | 15.4% |

Jigsaw is supplementary only. Its high bucket is distorted by mechanical mapping: only 11 of 50 high-mapped rows carry the threat label; 39 are severe-toxic/profanity-only rows.

## Prompt Tuning

Prompt v2 was chosen after one permitted change. On held-out fresh test rows, action accuracy improved from 78.3% to 87.0%, high/critical FNR improved from 22.2% to 5.6%, and normal FPR stayed 0.0%.

## Cost

Source: `evals/results/cost_report.csv`.

| Backend | Scenario | Token cost / 1,000 | Fallback cost / 1,000 | Total / 1,000 | Necessary review / 1,000 | p |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| keyword | platform_assumed | USD 0.00 | USD 18.58 | USD 18.58 | 0.875 | 0.972125 |
| LLM prompt_v2 cheap | platform_assumed | USD 0.064674 | USD 11.64 | USD 11.70 | 9.417 | 0.982542 |
| keyword | eval_observed_reference_only | USD 0.00 | USD 313.73 | USD 313.73 | 29.412 | 0.529412 |
| LLM prompt_v2 cheap | eval_observed_reference_only | USD 0.064654 | USD 78.43 | USD 78.50 | 362.745 | 0.882353 |

Break-even note: no frontier model was measured. With ASSUMED frontier prices and cheap measured token volume, frontier would need p* = 0.985403 compared with cheap p = 0.982542. Do not claim a frontier result.

All prices, platform prevalence, review time, reviewer wage, monthly volume, and missed-harm cost values are ASSUMED and must be verified before submission.
