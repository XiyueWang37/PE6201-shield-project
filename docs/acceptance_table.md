# Final Acceptance Table

| Requirement | Status | Evidence file | Remaining gap |
| --- | --- | --- | --- |
| LLM classifier interface with JSON prompt, cache before key lookup, usage, abstain | Done | `src/llm_classifier.py` | Needs a real valid LLM run in Phase B. |
| Deterministic policy mapping preserved | Done | `src/policy.py` | None. |
| Policy decision logging in one wrapper path | Done | `evals/run_eval.py`, `src/run_demo.py`, `src/policy.py` | Runtime logs remain ignored under `evals/logs/`. |
| Reproducible keyword evaluation | Done | `evals/run_eval.py`, `evals/latest/keyword_metrics_summary.csv` | Fresh human-reviewed slice not merged yet. |
| LLM fail-fast without key/cache | Done | `evals/run_eval.py` | Valid LLM metrics wait for Phase B. |
| Invalid no-key LLM result removed | Done | `docs/metrics_summary.md`, `evals/README.md` | Historical invalid run is noted but not used. |
| Context labels no longer counted from handwritten values | Done | `evals/context_eval_cases.csv`, timestamped `context_eval_results.csv` | Only 5 context cases until Phase C. |
| Lazy all-high baseline | Done | latest valid keyword `run_metadata.json` | None. |
| Abstention and API error accounting | Done | `evals/run_eval.py`, `run_metadata.json` | LLM model-abstain counts need real LLM run. |
| Public Jigsaw threat/profanity split | Done | latest valid keyword `public_jigsaw_metrics.json` | Mechanical mapping remains supplementary only. |
| Candidate data for human review | Done | `data/candidates_to_label.csv` | User must fill `shield_label` before merging. |
| Revised cost model | Done | `evals/cost_model.py`, `evals/test_cost_model.py`, `evals/results/cost_report.md` | Prices and prevalence assumptions must be verified. |
| Metric consistency check | Done | `evals/check_metrics_consistency.py` | Checks current docs and stale invalid references. |
| Report draft partially de-risked | Partial | `docs/final_report_draft.md` | Full final rewrite belongs to Phase D after valid LLM/fresh data. |
| Demo script | Partial | `demo/demo_script.md` | Full LLM-vs-keyword demo belongs to Phase D. |
