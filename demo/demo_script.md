# Shield Demo Script

Target length: 5 minutes. Show your face and screen.

## Before Recording

Open the GitHub repository and a Terminal in the project folder.

```bash
python3 src/run_demo.py
python3 evals/run_eval.py --backend keyword --jigsaw-n 300
python3 evals/cost_model.py
```

Open these files:

- `README.md`
- `docs/metrics_summary.md`
- `evals/results/cost_report.md`

## 0:00-0:30 Opening

Hi, my project is Shield, an AI-assisted harmful content intervention prototype for social media platforms. Shield classifies harassment severity in context and maps the label into allow, prompt reconsideration, or escalation to a human moderator.

## 0:30-1:15 Architecture

Show the mermaid architecture in `README.md`. Explain that the classifier estimates severity, but `src/policy.py` makes the action deterministic and auditable. Mention that the measured backend is the keyword fallback. The LLM interface exists, but no successful LLM call is reported without `SHIELD_API_KEY`.

## 1:15-2:20 Demo Cases

Run:

```bash
python3 src/run_demo.py
```

Show three cases:

1. Normal criticism: allowed.
2. Direct insult: medium, prompt reconsideration.
3. Context-sensitive case: the final comment is ambiguous alone but riskier with context.

Also name the failure: the keyword fallback under-escalates implicit threats. That is why this is a baseline, not a deployable classifier.

## 2:20-3:30 Metrics

Show `docs/metrics_summary.md`.

Key measured keyword results:

- High/critical FNR: 75.0%, which fails the safety target.
- Normal criticism FPR: 0.0%, which passes on a tiny sample.
- Exact accuracy: 66.7%.
- Macro F1: 0.395.
- Context strict accuracy: 80.0%.

Explain the lazy baseline: all-high gets 0.0% FNR but 100.0% FPR, proving that FNR alone can be gamed.

## 3:30-4:20 Cost

Show `evals/results/cost_report.md`.

The cost model uses ASSUMED prices that need verification. Under those assumptions, keyword fallback costs about USD 55.56 per 1,000 comments after expected human-review fallback. The LLM no-key path costs about USD 666.70 per 1,000 comments because every case abstains and escalates.

## 4:20-5:00 Closing

State the critique clearly: the current system is auditable and runnable, but the classifier is weak. The next step is human review of `data/candidates_to_label.csv`, expanding the core set to around 150 items, and rerunning both keyword and real LLM backends. The product should remain human-in-the-loop for severe and uncertain cases.
