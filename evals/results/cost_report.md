# Shield Cost Report

Currency: USD
Price date: 2026-10-04
Price source note: ASSUMED values for course prototype; verify against provider price pages before submission.

All model prices and human-review costs are ASSUMED and must be verified by the user against provider price pages before submission.

## Scenario Results

| Backend | Model tier | Cost / 1,000 comments | Cost / 1,000 successful decisions | Monthly cost | Success rate | Escalate rate | Abstention rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| keyword | cheap_assumed | 55.555556 | 60.606061 | 56155.56 | 0.9167 | 0.0833 | 0.0 |
| keyword | frontier_assumed | 55.555556 | 60.606061 | 56155.56 | 0.9167 | 0.0833 | 0.0 |
| llm | cheap_assumed | 666.697904 | inf | 667297.9 | 0.0 | 1.0 | 1.0 |
| llm | frontier_assumed | 667.707917 | inf | 668307.92 | 0.0 | 1.0 | 1.0 |

## Break-even Note

The cheap and frontier token tiers have the same observed success rate within a backend unless real LLM measurements are added. Break-even therefore depends on the frontier model improving success enough to offset its higher token price and any reduction in human review fallback.

## Sensitivity

See `cost_sensitivity.csv` for success-rate +/-10 percentage point scenarios.
