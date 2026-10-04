# Metrics Summary

All numbers in this file come from reproducible outputs under `evals/results/`. The current submission reports the keyword fallback as the measured runnable backend. The LLM backend interface exists, but no successful LLM call was measured because `SHIELD_API_KEY` was not set during evaluation.

## Core Prototype Eval

Source: `evals/results/20261004T082551Z_keyword/run_metadata.json`

| Metric | Target | Measured result | Interpretation |
| --- | ---: | ---: | --- |
| False negative rate on high/critical harassment | below 10% | 75.0% | 3 of 4 high/critical cases were not escalated. This fails the safety target. |
| False positive rate on normal criticism | below 15% | 0.0% | 0 of 4 normal criticism cases were prompted or escalated. This passes, but the sample is tiny. |
| Exact accuracy | reported | 66.7% | 8 of 12 examples matched the hand label. |
| Macro F1 | reported | 0.395 | Performance is weak across labels. |
| Abstention rate | reported | 0.0% | Keyword fallback never abstains. |
| Context strict accuracy | reported | 80.0% | 4 of 5 context movement cases matched the expected movement. |
| Context lenient accuracy | reported | 80.0% | 1 expected context escalation was missed. |

## Lazy Baseline

A lazy all-high baseline gets **0.0% FNR** on high/critical cases, but **100.0% FPR** on normal criticism. This shows why FNR alone is not enough: a system can look safe while over-escalating every ordinary criticism.

## Supplementary Public Jigsaw Eval

Source: `evals/results/20261004T082551Z_keyword/public_jigsaw_metrics.json`

The 300-row public Jigsaw sample is mechanically mapped from original Jigsaw labels into Shield labels. It is useful as a larger sanity check, but it is not hand-relabelled Shield ground truth.

| Supplementary metric | Result | Interpretation |
| --- | ---: | --- |
| Sample size | 300 | 100 normal, 100 medium, 50 high, 50 critical mapped examples. |
| Exact label accuracy | 38.7% | The fallback is too simple for broad public toxicity data. |
| Normal-reference false positive rate | 5.0% | It mostly avoids over-prompting non-toxic public samples. |
| High/critical false negative rate | 85.0% | It badly under-escalates severe mapped cases. |

## LLM Backend Status

Source: `evals/results/20261004T082500Z_llm/run_metadata.json`

The LLM backend was exercised without an API key. It therefore abstained on every case and escalated all cases by policy. This is a valid failure-path test, not evidence that an LLM performs better or worse than the keyword fallback.

## Cost

Source: `evals/results/cost_report.md`

The cost model uses ASSUMED prices and must be verified against provider price pages. Under current assumptions, keyword fallback costs about **USD 55.56 per 1,000 comments** after expected human review fallback. The no-key LLM path costs about **USD 666.70 per 1,000 comments** because every case abstains and goes to review.
