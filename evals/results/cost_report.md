# Shield Cost Report

Currency: USD
Price date: 2026-10-04
Price source note: ASSUMED values for course prototype; verify against provider price pages before submission.
Missed severe harm cost: ASSUMED 0; severe-miss harm is reported as risk, not modelled in the main cost.

All prices, review time, review wages, monthly volume, prevalence, and harm-cost values are ASSUMED and must be verified before submission.

## Scenario Results

| Backend | Model tier | Prevalence | p | Token cost / 1,000 | Fallback cost / 1,000 | Total / 1,000 | Necessary review / 1,000 | FN rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| keyword | local_rules | platform_assumed | 0.972125 | 0.0 | 18.583333 | 18.583333 | 0.875 | 0.009125 |
| keyword | local_rules | eval_observed_reference_only | 0.529412 | 0.0 | 313.72549 | 313.72549 | 29.412 | 0.352941 |
| llm | cheap_assumed | platform_assumed | 0.982542 | 0.064674 | 11.638889 | 11.703563 | 9.417 | 0.000583 |
| llm | cheap_assumed | eval_observed_reference_only | 0.882353 | 0.064654 | 78.431373 | 78.496027 | 362.745 | 0.019608 |

## Break-even

Frontier required p*: 0.985403; observed cheap p: 0.982542; observed frontier p: not measured. No frontier result was measured; do not claim frontier wins or loses.
Note: uses cheap measured token volume with frontier ASSUMED token prices.

## Unmeasured Tiers

- frontier_assumed (not_chosen_not_measured): not measured. No valid run for this tier; excluded from scenario table and no p reused from another tier.

See `cost_sensitivity.csv` and `cost_prevalence_sensitivity.csv` for sensitivity tables.
