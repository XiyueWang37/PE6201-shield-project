# Evaluation Files

Run the keyword baseline:

```bash
python3 evals/run_eval.py --backend keyword --jigsaw-n 300
```

Run the LLM backend. If all needed cache entries exist, no key is required; otherwise set `SHIELD_API_KEY` first:

```bash
export SHIELD_API_KEY="..."
export SHIELD_LLM_MODEL="openai/gpt-4o-mini"
python3 evals/run_eval.py --backend llm --jigsaw-n 300
```

Prompt v2 is the default submitted prompt. To reproduce the tuning baseline:

```bash
SHIELD_PROMPT_VERSION=prompt_v1 python3 evals/run_eval.py --backend llm --jigsaw-n 300
```

If `SHIELD_API_KEY` is missing and cache entries are missing, the LLM runner exits with a non-zero status and does not create a result directory.

## Current Layout

- `run_eval.py`: reproducible evaluation runner.
- `merge_candidates.py`: derives `data/core_eval_set.csv` and appends confirmed thread cases without editing source files.
- `cost_model.py`: platform cost model using valid measured runs and ASSUMED prices.
- `test_cost_model.py`: unit tests for cost semantics.
- `prompt_tuning_summary.csv`: v1 vs v2 dev/test prompt tuning results.
- `latest/`: backend-specific latest outputs. These replace the old top-level overwrite pattern.
- `results/`: timestamped reproducible outputs.
- `legacy/`: old top-level Jigsaw CSV summaries retained for traceability. They are superseded by timestamped `results/*/public_jigsaw_*` files.
- `cache/`: committed LLM response cache. It contains comment text and model output, but no API key. Cache hits return before `SHIELD_API_KEY` is required; cache misses require a key.
- `logs/`: ignored runtime policy-decision logs.

## Final Valid Runs

- Keyword final fresh run: `evals/results/20261004T093323Z_keyword/`
- LLM prompt_v1 replay: `evals/results/20261004T094339Z_llm/`
- LLM prompt_v2 final replay: `evals/results/20261004T100146Z_llm/`

## Headline Results

Fresh slice headline:

- Keyword FNR 94.3%, FPR 0.0%, macro F1 0.224, context strict accuracy 58.8%.
- LLM prompt_v2 FNR 5.7%, FPR 0.0%, macro F1 0.617, context strict accuracy 82.4%.

The old no-key LLM run produced 100% abstention because credentials were missing. It was invalidated and must not be used for metrics or cost claims.
