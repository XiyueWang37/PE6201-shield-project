# Shield Demo Script

Target length: 5 minutes. Show your face and screen while explaining.

## Before Recording

Open the GitHub repository and a Terminal in the project folder.

```bash
python3 src/run_demo.py
python3 evals/run_eval.py --backend keyword --jigsaw-n 300
python3 evals/run_eval.py --backend llm --jigsaw-n 300
python3 evals/cost_model.py
```

Open these files:

- `README.md`
- `docs/metrics_summary.md`
- `evals/results/cost_report.md`
- `docs/prompt_tuning.md`

## 0:00-0:30 Opening

Hi, my project is Shield, an AI-assisted harmful content intervention prototype for social media platforms. Shield classifies harassment severity in context and maps the label into allow, prompt reconsideration, or escalation to a human moderator.

## 0:30-1:10 Architecture

Show the architecture in `README.md`. Explain that the classifier estimates severity, but `src/policy.py` makes the final product action deterministic and auditable. Point out the two measured backends: keyword baseline and LLM prompt_v2.

## 1:10-2:05 Demo Cases

Run:

```bash
python3 src/run_demo.py
```

Show three cases:

1. Normal criticism: allowed.
2. Direct insult: medium, prompt reconsideration.
3. Context-sensitive case: the final comment becomes riskier in context.

## 2:05-3:10 Metrics

Show `docs/metrics_summary.md`.

Fresh slice headline:

- Keyword FNR: 94.3%; LLM v2 FNR: 5.7%.
- Keyword FPR: 0.0%; LLM v2 FPR: 0.0%.
- Keyword macro F1: 0.224; LLM v2 macro F1: 0.617.
- Keyword context strict/lenient: 58.8% / 58.8%; LLM v2: 82.4% / 88.2%.

Explain the lazy baseline: all-high gets 0.0% FNR but 100.0% FPR, proving that FNR alone can be gamed.

## 3:10-3:45 Failure Case

Show one real LLM v2 failure from `evals/results/20261004T100146Z_llm/eval_cases.csv`: `I am going to be outside after the meeting.` Gold is high/escalate, but LLM predicted normal/allow. This shows the model still misses some implicit offline threats.

## 3:45-4:25 Prompt Tuning

Show `docs/prompt_tuning.md`. Explain that v1 under-labelled direct insults and implicit threats. One prompt change added boundary calibration. On held-out test, action accuracy improved from 78.3% to 87.0%, FNR improved from 22.2% to 5.6%, and FPR stayed 0.0%.

## 4:25-4:50 Cost

Show `evals/results/cost_report.md`. Under ASSUMED platform prevalence and review-cost assumptions, keyword costs USD 18.58 per 1,000 comments; LLM v2 costs USD 11.70 per 1,000, including USD 0.064674 token cost and expected fallback cost.

## 4:50-5:00 Closing

Close with the critique: Shield is auditable and the LLM improves substantially over keywords on the fresh slice, but the evaluation is still small, single-reviewer, and partly AI-drafted. The deployment path should remain human-in-the-loop.
