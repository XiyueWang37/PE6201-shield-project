# Evaluation Explanation

Shield is evaluated as a product intervention, not only as a classifier. The key question is whether it catches severe harm without over-prompting normal users.

## How to Run

Keyword backend, no API key required:

```bash
python3 evals/run_eval.py --backend keyword --jigsaw-n 300
```

LLM backend, API key required:

```bash
export SHIELD_API_KEY="..."
python3 evals/run_eval.py --backend llm --jigsaw-n 0
```

Cost model:

```bash
python3 evals/cost_model.py
```

## Files

- `run_eval.py`: reproducible evaluation runner for keyword and LLM backends.
- `cost_model.py`: cost model using measured usage/action outputs and ASSUMED prices.
- `eval_cases.csv`: latest core eval output written by `run_eval.py`.
- `context_eval_cases.csv`: context test inputs. Old hand-written labels have been renamed to `legacy_handwritten_*` and are not used for metrics.
- `metrics_summary.csv`: latest core metrics written by `run_eval.py`.
- `public_jigsaw_eval_300.csv`: earlier supplementary public Jigsaw eval output.
- `public_jigsaw_metrics_300.csv`: earlier supplementary public Jigsaw metrics.
- `results/`: timestamped reproducible outputs, including confusion matrices, run metadata, context movement results, and cost reports.

## Current Measured Results

Latest keyword run: `evals/results/20261004T082551Z_keyword/`

- High/critical FNR: 75.0% (3 of 4 missed)
- Normal criticism FPR: 0.0% (0 of 4 over-prompted)
- Exact accuracy: 66.7%
- Macro F1: 0.395
- Context strict/lenient accuracy: 80.0%
- Lazy all-high baseline: 0.0% FNR but 100.0% FPR

LLM run: `evals/results/20261004T082500Z_llm/`

- No API key was present, so every case abstained and escalated.
- This is a failure-path test, not a valid LLM performance comparison.

## Known Limitations

The core labelled set is still very small. The public Jigsaw sample uses mechanical label mapping, not Shield-specific human relabelling. The keyword fallback appears tuned to test examples and uses substring matching, so words such as `diet` or `skill` can trigger `die` or `kill` matches. Report these weaknesses rather than hiding them.
