# Evaluation Files

Run the keyword baseline:

```bash
python3 evals/run_eval.py --backend keyword --jigsaw-n 300
```

Run the LLM backend only after a real key is configured or all needed cache entries already exist:

```bash
export SHIELD_API_KEY="..."
python3 evals/run_eval.py --backend llm --jigsaw-n 300
```

If `SHIELD_API_KEY` is missing and cache entries are missing, the LLM runner exits with a non-zero status and does not create a result directory.

## Current Layout

- `run_eval.py`: reproducible evaluation runner.
- `cost_model.py`: platform cost model using valid measured runs and ASSUMED prices.
- `test_cost_model.py`: unit tests for cost semantics.
- `latest/`: backend-specific latest outputs. These replace the old top-level `eval_cases.csv` and `metrics_summary.csv` overwrite pattern.
- `results/`: timestamped reproducible outputs.
- `legacy/`: old top-level Jigsaw CSV summaries retained for traceability. They are superseded by timestamped `results/*/public_jigsaw_*` files.
- `cache/`: committed LLM response cache. It contains comment text and model output, but no API key. Cache hits return before `SHIELD_API_KEY` is required; cache misses require a key.
- `logs/`: ignored runtime policy-decision logs.

## Invalidated Result

A previous no-key LLM run produced 100% abstention because credentials were missing. That run was deleted and must not be used for metrics or cost claims.
