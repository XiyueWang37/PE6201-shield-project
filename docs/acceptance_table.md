# Final Acceptance Table

| Requirement | Status | Evidence file | Remaining gap |
| --- | --- | --- | --- |
| Deterministic policy mapping preserved | Done | `src/policy.py` | None. |
| Keyword baseline retained without behavior tuning | Done | `src/shield_classifier.py` | Weaknesses documented. |
| LLM classifier with JSON prompt, cache before key lookup, usage, abstain | Done | `src/llm_classifier.py`, `evals/cache/llm_responses.jsonl` | None. |
| LLM fail-fast without key/cache | Done | `evals/run_eval.py` | None. |
| No-key replay from committed cache | Done | `evals/results/20261004T100146Z_llm/run_metadata.json` | None. |
| Human-reviewed candidate merge | Done | `data/candidates_to_label.csv`, `data/core_eval_set.csv`, `evals/merge_candidates.py` | Single reviewer; labels confirmed from AI draft. |
| Fresh/original/combined slices | Done | `evals/latest/*_metrics_summary.csv` | Hard-normal slice has n=0. |
| Context eval expanded | Done | `evals/context_eval_cases.csv` | 17 total context cases. |
| Prompt tuning exactly once | Done | `docs/prompt_tuning.md`, `data/split_ids.csv`, `evals/prompt_tuning_summary.csv` | None. |
| Public Jigsaw threat/profanity split | Done | `public_jigsaw_metrics.json`, `data/README.md` | Mechanical mapping remains supplementary only. |
| Lazy all-high baseline | Done | `run_metadata.json` files | None. |
| Cost model with platform prevalence and valid-run filtering | Done | `evals/cost_model.py`, `evals/results/cost_report.csv` | ASSUMED prices and prevalence need user verification. |
| Frontier tier not reused from cheap | Done | `evals/results/cost_unmeasured_tiers.csv`, `cost_break_even.csv` | No measured frontier run. |
| Unit tests | Done | `evals/test_cost_model.py` | None. |
| Report and demo documentation | Done | `docs/final_report_draft.md`, `docs/final_report.pdf`, `demo/demo_script.md` | User must record demo video. |
| Metric consistency check | Done | `evals/check_metrics_consistency.py` | None after final docs sync. |
