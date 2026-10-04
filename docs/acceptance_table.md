# Final Acceptance Table

| Requirement | Status | Evidence file | Remaining gap |
| --- | --- | --- | --- |
| LLM classifier interface with JSON prompt, cache, usage, abstain | Done | `src/llm_classifier.py` | No successful LLM run without `SHIELD_API_KEY`. |
| Deterministic policy mapping preserved | Done | `src/policy.py` | None. |
| Policy decision logging | Done | `src/policy.py`, ignored `evals/logs/` | Logs are runtime artifacts and not committed. |
| Reproducible keyword evaluation | Done | `evals/run_eval.py`, `evals/results/20261004T082551Z_keyword/` | Core labelled set remains small. |
| LLM backend evaluation path | Partial | `evals/results/20261004T082500Z_llm/` | No API key, so abstention rate is 100%; no valid LLM quality comparison. |
| Context labels no longer counted from handwritten values | Done | `evals/context_eval_cases.csv`, `evals/results/*/context_eval_results.csv` | Only 5 context cases. |
| Lazy all-high baseline | Done | `evals/results/20261004T082551Z_keyword/run_metadata.json` | None. |
| Abstention rate | Done | `evals/results/*/run_metadata.json` | LLM abstention reflects missing key. |
| Public supplementary data | Done | `data/public_jigsaw_sample_300.csv` | Mechanical mapping, not hand-labelled Shield truth. |
| Candidate data for human review | Done | `data/candidates_to_label.csv` | User must fill `shield_label` before merging. |
| Cost model | Done | `evals/cost_model.py`, `evals/results/cost_report.md` | Prices and human-review assumptions must be verified. |
| Report updated from measured outputs | Done | `docs/final_report_draft.md`, `docs/final_report.pdf` | Visual PDF render not rerun due font cache issue; PDF text/page checks pass. |
| Demo script updated | Done | `demo/demo_script.md` | User still needs to record video. |
| Metric consistency check | Done | `evals/check_metrics_consistency.py` | Checks headline numbers only. |
