# Shield Cost Report

Currency: USD
Price date: 2026-10-04
Price source note: ASSUMED values for course prototype; verify against provider price pages before submission.
Missed severe harm cost: ASSUMED 0; severe-miss harm is reported as risk, not modelled in the main cost.

All prices, review time, review wages, monthly volume, prevalence, and harm-cost values are ASSUMED and must be verified before submission.

## Scenario Results

| Backend | Model tier | Prevalence | p | Token cost / 1,000 | Fallback cost / 1,000 | Total / 1,000 | Necessary review / 1,000 | FN rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| keyword | local_rules | platform_assumed | 0.984833 | 0.0 | 10.111111 | 10.111111 | 2.333 | 0.007667 |
| keyword | local_rules | eval_observed_reference_only | 0.666667 | 0.0 | 222.222222 | 222.222222 | 83.333 | 0.25 |
| llm | cheap_assumed | platform_assumed | 0.9925 | 0.05633 | 5.0 | 5.05633 | 10.0 | 0.0 |
| llm | cheap_assumed | eval_observed_reference_only | 0.916667 | 0.057437 | 55.555556 | 55.612993 | 333.333 | 0.0 |

## Break-even

Frontier required p*: 0.994904; observed cheap p: 0.9925; observed frontier p: not measured. No frontier result was measured; do not claim frontier wins or loses.
Note: uses cheap measured token volume with frontier ASSUMED token prices.

## Unmeasured Tiers

- frontier_assumed (not_chosen_not_measured): not measured. No valid run for this tier; excluded from scenario table and no p reused from another tier.

See `cost_sensitivity.csv` and `cost_prevalence_sensitivity.csv` for sensitivity tables.
