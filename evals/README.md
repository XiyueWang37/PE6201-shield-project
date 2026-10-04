# Evaluation Explanation

Shield is evaluated as a product intervention, not only as a classifier. The key question is whether it catches severe harm without over-prompting normal users.

## Metrics

1. False negative rate on high/critical harassment.
   - Measures severe harmful comments incorrectly allowed or under-classified.
   - Target: below 10%.

2. False positive or over-prompt rate on normal criticism.
   - Measures normal criticism incorrectly prompted or escalated.
   - Target: below 15-20%.

3. Context-sensitivity test.
   - Run each thread twice: final comment alone, then final comment with context.
   - Report whether the severity label moves correctly.

4. Cost per 1,000 comments.
   - Estimate from measured average tokens per comment and provider model pricing.
   - This answers whether the system is viable at platform volume.

## Files

- `eval_cases.csv`: small hand-labelled single-comment evaluation cases and prototype predictions.
- `context_eval_cases.csv`: context movement cases.
- `metrics_summary.csv`: target and result summary for the core prototype eval.
- `public_jigsaw_eval_300.csv`: supplementary 300-row public Jigsaw eval using mechanically mapped Shield labels.
- `public_jigsaw_metrics_300.csv`: supplementary metrics from the 300-row public Jigsaw eval.
