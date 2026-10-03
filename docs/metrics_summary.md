# Metrics Summary

This project evaluates Shield as a product intervention, not only as a classifier. A system that flags everything as high severity can look good on false negatives while making the product unusable through over-prompting. For that reason, the final evaluation reports both severe-harm misses and normal-criticism over-prompting.

| Metric | Target | Current prototype result | Interpretation |
| --- | ---: | ---: | --- |
| False negative rate on high/critical harassment | below 10% | 75% | The local fallback misses implicit threats, so the final design needs a contextual LLM classifier and human review. |
| False positive rate on normal criticism | below 15-20% | 0% | Normal criticism was not over-prompted in the small eval set. |
| Overall accuracy | report | 66.7% | 8 of 12 small eval cases matched the hand label. |
| Context movement design accuracy | report | 100% | The context eval set directly tests final-comment-only versus full-context judgement. |
| Cost per 1,000 comments | report | estimated below USD 0.10 | Replace with measured token usage if available. |

## Cost Formula

```text
cost per 1,000 comments =
((average input tokens * input price per token)
+ (average output tokens * output price per token))
* 1,000
```

For the course submission, this value should be presented as either measured from provider usage logs or estimated with explicit assumptions. The key point is to show that Shield has been evaluated at platform scale, not only as a single-comment demo.

## Main Critique

The current deterministic fallback is useful for demonstrating the system architecture, but it is not strong enough as the final classifier. It avoids over-prompting normal criticism, but it misses implicit threats such as location-based intimidation. This supports the product design choice: use a foundation model for contextual severity judgement, then pass the structured severity label into a deterministic policy table for auditable action selection.
