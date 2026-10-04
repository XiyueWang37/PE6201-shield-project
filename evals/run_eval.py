"""Reproducible evaluation runner for Shield.

The runner evaluates keyword or LLM backends, writes immutable timestamped
results under `evals/results/`, and writes backend-specific latest files under
`evals/latest/`. It never creates an LLM result directory when credentials and
cache are insufficient for a valid run.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from policy import log_decision  # noqa: E402

LABELS = ["normal", "low", "medium", "high", "critical"]
RANK = {label: idx for idx, label in enumerate(LABELS)}
ACTIONS = {
    "normal": "allow",
    "low": "allow",
    "medium": "prompt_reconsider",
    "high": "escalate_to_moderator",
    "critical": "escalate_to_moderator",
    "abstain": "escalate_to_moderator",
}
FPR_CEILING = 0.15
HARD_NORMAL_TYPES = {"non_targeted_profanity", "sarcasm", "idea_targeted_insult"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: list[str] = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.append(key)
        fieldnames = seen
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_label(label: str) -> str:
    label = (label or "").strip().lower()
    return label if label in LABELS else "abstain"


def gold_action(label: str) -> str:
    return ACTIONS[normalize_label(label)]


def positive_action(action: str) -> bool:
    return action in {"prompt_reconsider", "escalate_to_moderator"}


def import_backend(name: str):
    if name == "keyword":
        return importlib.import_module("shield_classifier")
    if name == "llm":
        return importlib.import_module("llm_classifier")
    raise ValueError(name)


def classify(backend_module, backend_name: str, comment: str, context: str = ""):
    result = backend_module.classify_comment(comment, context)
    log_decision(comment, context, result.severity, result.policy_action, backend_name)
    return result


def binom_cdf(k: int, n: int, p: float) -> float:
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    total = 0.0
    for i in range(k + 1):
        total += math.comb(n, i) * (p**i) * ((1 - p) ** (n - i))
    return total


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    if k == 0:
        lower = 0.0
    else:
        lo, hi = 0.0, k / n
        for _ in range(80):
            mid = (lo + hi) / 2
            if 1 - binom_cdf(k - 1, n, mid) > alpha / 2:
                hi = mid
            else:
                lo = mid
        lower = (lo + hi) / 2
    if k == n:
        upper = 1.0
    else:
        lo, hi = k / n, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            if binom_cdf(k, n, mid) < alpha / 2:
                hi = mid
            else:
                lo = mid
        upper = (lo + hi) / 2
    return lower, upper


def macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    scores = []
    for label in LABELS:
        tp = sum(t == label and p == label for t, p in zip(y_true, y_pred))
        fp = sum(t != label and p == label for t, p in zip(y_true, y_pred))
        fn = sum(t == label and p != label for t, p in zip(y_true, y_pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return sum(scores) / len(scores)


def confusion_matrix(y_true: list[str], y_pred: list[str]) -> list[dict[str, object]]:
    rows = []
    for true_label in LABELS:
        row: dict[str, object] = {"true_label": true_label}
        for pred_label in LABELS + ["abstain"]:
            row[pred_label] = sum(t == true_label and p == pred_label for t, p in zip(y_true, y_pred))
        rows.append(row)
    return rows


def bool_text(value: object) -> str:
    return str(value).strip().lower()


def load_core_rows() -> list[dict[str, str]]:
    core_path = ROOT / "data" / "core_eval_set.csv"
    if core_path.exists():
        rows = read_csv(core_path)
    else:
        rows = read_csv(ROOT / "data" / "relabelled_eval_set.csv")
        for row in rows:
            row.setdefault("hard_case_type", "")
            row["tuned_on"] = "true"
            row.setdefault("source", row.get("source_dataset", "manual_original"))
    return rows


def row_true_label(row: dict[str, str]) -> str:
    return normalize_label(row.get("shield_label") or row.get("shield_label_mapped") or row.get("true_label"))


def evaluate_rows(rows: list[dict[str, str]], backend_module, backend_name: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    outputs: list[dict[str, object]] = []
    y_true: list[str] = []
    y_pred: list[str] = []
    start = time.time()
    for row in rows:
        result = classify(backend_module, backend_name, row["comment"], row.get("context", ""))
        true_label = row_true_label(row)
        pred_label = normalize_label(result.severity)
        expected_action = gold_action(true_label)
        action_correct = (result.policy_action == expected_action) and not bool(getattr(result, "abstain", False))
        y_true.append(true_label)
        y_pred.append(pred_label)
        output = {
            "id": row.get("id") or row.get("sample_id"),
            "source": row.get("source") or row.get("source_dataset", ""),
            "comment": row["comment"],
            "context": row.get("context", ""),
            "true_label": true_label,
            "gold_action": expected_action,
            "predicted_label": pred_label,
            "policy_action": result.policy_action,
            "action_correct": action_correct,
            "confidence": result.confidence,
            "is_normal_criticism": bool_text(row.get("is_normal_criticism", true_label == "normal")),
            "is_high_or_critical": bool_text(row.get("is_high_or_critical", true_label in {"high", "critical"})),
            "hard_case_type": row.get("hard_case_type", ""),
            "tuned_on": bool_text(row.get("tuned_on", "false")),
            "correct": pred_label == true_label,
            "abstain": bool(getattr(result, "abstain", False)),
            "error_type": getattr(result, "error_type", ""),
            "input_tokens": int(getattr(result, "input_tokens", 0)),
            "output_tokens": int(getattr(result, "output_tokens", 0)),
            "rationale": result.rationale,
        }
        for key, value in row.items():
            if key.startswith("jigsaw_") or key in {"shield_label_mapped", "sample_slice", "mapping_notes"}:
                output[key] = value
        outputs.append(output)
    elapsed = time.time() - start
    metrics = metric_summary(outputs, y_true, y_pred, elapsed)
    return outputs, metrics


def metric_summary(outputs: list[dict[str, object]], y_true: list[str], y_pred: list[str], elapsed: float) -> dict[str, object]:
    normal = [r for r in outputs if bool_text(r.get("is_normal_criticism")) == "true"]
    high = [r for r in outputs if bool_text(r.get("is_high_or_critical")) == "true"]
    hard_normal = [r for r in normal if str(r.get("hard_case_type", "")) in HARD_NORMAL_TYPES]
    fp = sum(1 for r in normal if positive_action(str(r["policy_action"])))
    fn = sum(1 for r in high if r["policy_action"] != "escalate_to_moderator")
    hard_fp = sum(1 for r in hard_normal if positive_action(str(r["policy_action"])))
    fpr = fp / len(normal) if normal else 0.0
    fnr = fn / len(high) if high else 0.0
    hard_fpr = hard_fp / len(hard_normal) if hard_normal else 0.0
    fpr_ci = clopper_pearson(fp, len(normal)) if normal else (0.0, 0.0)
    fnr_ci = clopper_pearson(fn, len(high)) if high else (0.0, 0.0)
    hard_ci = clopper_pearson(hard_fp, len(hard_normal)) if hard_normal else (0.0, 0.0)
    abstain = sum(1 for r in outputs if r["abstain"])
    api_errors = sum(1 for r in outputs if r.get("error_type") == "api_error")
    model_abstain = sum(1 for r in outputs if r.get("error_type") == "model_abstain")
    action_correct = sum(1 for r in outputs if r.get("action_correct") is True)
    return {
        "n": len(outputs),
        "elapsed_seconds": round(elapsed, 3),
        "false_positive_count": fp,
        "normal_n": len(normal),
        "false_positive_rate": fpr,
        "false_positive_ci_low": fpr_ci[0],
        "false_positive_ci_high": fpr_ci[1],
        "false_positive_target": FPR_CEILING,
        "false_positive_pass": fpr <= FPR_CEILING,
        "false_negative_count": fn,
        "high_critical_n": len(high),
        "false_negative_rate": fnr,
        "false_negative_ci_low": fnr_ci[0],
        "false_negative_ci_high": fnr_ci[1],
        "hard_normal_n": len(hard_normal),
        "hard_normal_false_positive_count": hard_fp,
        "hard_normal_false_positive_rate": hard_fpr,
        "hard_normal_false_positive_ci_low": hard_ci[0],
        "hard_normal_false_positive_ci_high": hard_ci[1],
        "accuracy": sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true) if y_true else 0.0,
        "action_accuracy": action_correct / len(outputs) if outputs else 0.0,
        "macro_f1": macro_f1(y_true, y_pred) if y_true else 0.0,
        "abstention_rate": abstain / len(outputs) if outputs else 0.0,
        "api_error_count": api_errors,
        "abstain_by_model_count": model_abstain,
        "avg_input_tokens": sum(float(r.get("input_tokens") or 0) for r in outputs) / len(outputs) if outputs else 0.0,
        "avg_output_tokens": sum(float(r.get("output_tokens") or 0) for r in outputs) / len(outputs) if outputs else 0.0,
    }


def metrics_for_slice(outputs: list[dict[str, object]], name: str, predicate) -> dict[str, object]:
    rows = [r for r in outputs if predicate(r)]
    y_true = [str(r["true_label"]) for r in rows]
    y_pred = [str(r["predicted_label"]) for r in rows]
    metrics = metric_summary(rows, y_true, y_pred, 0.0)
    metrics["slice"] = name
    return metrics


def lazy_baseline_metrics(rows: list[dict[str, str]]) -> dict[str, object]:
    outputs = []
    for row in rows:
        true_label = row_true_label(row)
        outputs.append(
            {
                "is_normal_criticism": bool_text(row.get("is_normal_criticism", true_label == "normal")),
                "is_high_or_critical": bool_text(row.get("is_high_or_critical", true_label in {"high", "critical"})),
                "hard_case_type": row.get("hard_case_type", ""),
                "policy_action": "escalate_to_moderator",
                "action_correct": gold_action(true_label) == "escalate_to_moderator",
                "abstain": False,
                "error_type": "",
            }
        )
    y_true = [row_true_label(row) for row in rows]
    y_pred = ["high" for _ in rows]
    return metric_summary(outputs, y_true, y_pred, 0.0)


def evaluate_context(rows: list[dict[str, str]], backend_module, backend_name: str) -> list[dict[str, object]]:
    out = []
    for row in rows:
        without = classify(backend_module, backend_name, row["final_comment"], "")
        with_context = classify(backend_module, backend_name, row["final_comment"], row["preceding_context"])
        label_without = normalize_label(without.severity)
        label_with = normalize_label(with_context.severity)
        movement = "escalate" if RANK.get(label_with, -1) > RANK.get(label_without, -1) else "no_change"
        expected = row.get("expected_movement", "").strip().lower()
        strict_ok = movement == expected
        lenient_ok = True if expected == "no_change" and movement == "no_change" else RANK.get(label_with, -1) > RANK.get(label_without, -1)
        out.append(
            {
                "id": row.get("id"),
                "preceding_context": row["preceding_context"],
                "final_comment": row["final_comment"],
                "legacy_handwritten_label_without_context": row.get("legacy_handwritten_label_without_context", ""),
                "legacy_handwritten_label_with_context": row.get("legacy_handwritten_label_with_context", ""),
                "expected_movement": expected,
                "label_without_context": label_without,
                "label_with_context": label_with,
                "movement_observed": movement,
                "strict_correct": strict_ok,
                "lenient_correct": lenient_ok,
                "missed_expected_change": expected == "escalate" and movement != "escalate",
                "without_error_type": getattr(without, "error_type", ""),
                "with_error_type": getattr(with_context, "error_type", ""),
                "backend": backend_name,
            }
        )
    return out


def context_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {"context_n": 0, "strict_accuracy": 0.0, "lenient_accuracy": 0.0, "missed_expected_changes": 0, "api_error_count": 0}
    return {
        "context_n": len(rows),
        "strict_accuracy": sum(bool(r["strict_correct"]) for r in rows) / len(rows),
        "lenient_accuracy": sum(bool(r["lenient_correct"]) for r in rows) / len(rows),
        "missed_expected_changes": sum(bool(r["missed_expected_change"]) for r in rows),
        "api_error_count": sum(1 for r in rows if r.get("without_error_type") == "api_error")
        + sum(1 for r in rows if r.get("with_error_type") == "api_error"),
    }


def jigsaw_extra_metrics(outputs: list[dict[str, object]]) -> dict[str, object]:
    threat_rows = [r for r in outputs if str(r.get("jigsaw_threat", "0")) == "1"]
    threat_missed = sum(1 for r in threat_rows if r.get("policy_action") != "escalate_to_moderator")
    profanity_high = [
        r
        for r in outputs
        if r.get("shield_label_mapped") == "high" and str(r.get("jigsaw_threat", "0")) == "0"
    ]
    profanity_upgraded = sum(1 for r in profanity_high if r.get("policy_action") == "escalate_to_moderator")
    return {
        "jigsaw_threat_flagged_n": len(threat_rows),
        "jigsaw_threat_flagged_false_negative_count": threat_missed,
        "jigsaw_threat_flagged_false_negative_rate": threat_missed / len(threat_rows) if threat_rows else 0.0,
        "jigsaw_profanity_only_high_n": len(profanity_high),
        "jigsaw_profanity_only_high_upgrade_count": profanity_upgraded,
        "jigsaw_profanity_only_high_upgrade_rate": profanity_upgraded / len(profanity_high) if profanity_high else 0.0,
        "notes": "These subsets separate actual Jigsaw threat flags from severe-toxic/profanity-only rows mapped to Shield high.",
    }


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def metric_rows(backend_name: str, slice_metrics: dict[str, dict[str, object]], context_summary: dict[str, object], lazy: dict[str, object], jigsaw_metrics: dict[str, object] | None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [{"metric": "backend", "slice": "run", "target": "reported", "result": backend_name, "notes": "Evaluation backend."}]
    for slice_name, metrics in slice_metrics.items():
        rows.extend(
            [
                {"metric": "false_negative_rate_high_critical", "slice": slice_name, "target": "<10%", "result": format_pct(float(metrics["false_negative_rate"])), "notes": f"{metrics['false_negative_count']} of {metrics['high_critical_n']} high/critical cases were not escalated. 95% CI {format_pct(float(metrics['false_negative_ci_low']))}-{format_pct(float(metrics['false_negative_ci_high']))}."},
                {"metric": "false_positive_rate_normal_criticism", "slice": slice_name, "target": "<15%", "result": format_pct(float(metrics["false_positive_rate"])), "notes": f"{metrics['false_positive_count']} of {metrics['normal_n']} normal criticism cases were prompted/escalated. PASS={metrics['false_positive_pass']}. 95% CI {format_pct(float(metrics['false_positive_ci_low']))}-{format_pct(float(metrics['false_positive_ci_high']))}."},
                {"metric": "hard_normal_false_positive_rate", "slice": slice_name, "target": "reported", "result": format_pct(float(metrics["hard_normal_false_positive_rate"])), "notes": f"{metrics['hard_normal_false_positive_count']} of {metrics['hard_normal_n']} hard-normal cases were prompted/escalated."},
                {"metric": "action_accuracy", "slice": slice_name, "target": "reported", "result": format_pct(float(metrics["action_accuracy"])), "notes": "Predicted action equals gold policy action and does not abstain."},
                {"metric": "overall_accuracy", "slice": slice_name, "target": "reported", "result": format_pct(float(metrics["accuracy"])), "notes": "Exact severity match."},
                {"metric": "macro_f1", "slice": slice_name, "target": "reported", "result": f"{float(metrics['macro_f1']):.3f}", "notes": "Macro F1 across severity labels."},
                {"metric": "abstention_rate", "slice": slice_name, "target": "reported", "result": format_pct(float(metrics["abstention_rate"])), "notes": "Rate of backend abstention."},
            ]
        )
    rows.extend(
        [
            {"metric": "lazy_baseline_fnr_high_critical", "slice": "combined", "target": "critique", "result": format_pct(float(lazy["false_negative_rate"])), "notes": "All-high baseline shows FNR can be gamed."},
            {"metric": "lazy_baseline_fpr_normal_criticism", "slice": "combined", "target": "critique", "result": format_pct(float(lazy["false_positive_rate"])), "notes": "All-high baseline over-prompts all normal criticism."},
            {"metric": "context_strict_accuracy", "slice": "context", "target": "reported", "result": format_pct(float(context_summary["strict_accuracy"])), "notes": f"Strict movement result over {context_summary['context_n']} context cases."},
            {"metric": "context_lenient_accuracy", "slice": "context", "target": "reported", "result": format_pct(float(context_summary["lenient_accuracy"])), "notes": f"Lenient movement result; missed expected changes={context_summary['missed_expected_changes']}."},
        ]
    )
    if jigsaw_metrics:
        rows.extend(
            [
                {"metric": "jigsaw_threat_flagged_fnr", "slice": "public_jigsaw", "target": "reported", "result": format_pct(float(jigsaw_metrics["jigsaw_threat_flagged_false_negative_rate"])), "notes": f"{jigsaw_metrics['jigsaw_threat_flagged_false_negative_count']} of {jigsaw_metrics['jigsaw_threat_flagged_n']} Jigsaw threat-flagged rows were not escalated."},
                {"metric": "jigsaw_profanity_only_high_upgrade_rate", "slice": "public_jigsaw", "target": "reported", "result": format_pct(float(jigsaw_metrics["jigsaw_profanity_only_high_upgrade_rate"])), "notes": f"{jigsaw_metrics['jigsaw_profanity_only_high_upgrade_count']} of {jigsaw_metrics['jigsaw_profanity_only_high_n']} high-mapped rows without Jigsaw threat were escalated. {jigsaw_metrics['notes']}"},
            ]
        )
    return rows


def maybe_rename_context_columns(path: Path) -> None:
    rows = read_csv(path)
    if not rows or "label_without_context" not in rows[0]:
        return
    new_rows = []
    for row in rows:
        copied = dict(row)
        copied["legacy_handwritten_label_without_context"] = copied.pop("label_without_context", "")
        copied["legacy_handwritten_label_with_context"] = copied.pop("label_with_context", "")
        new_rows.append(copied)
    write_csv(path, new_rows)


def preflight_or_exit(backend_name: str, backend_module, planned_rows: list[dict[str, str]]) -> dict[str, object]:
    if backend_name != "llm":
        return {"model": "keyword_local", "model_tier": "local_rules", "base_url": "", "prompt_version": "keyword_v1", "estimated_cost_usd": 0.0, "call_count": len(planned_rows)}
    preflight = backend_module.preflight_for_rows(planned_rows)
    print(json.dumps({"llm_preflight": preflight}, indent=2))
    if float(preflight["estimated_cost_usd"]) > 2:
        raise SystemExit("Estimated LLM cost exceeds USD 2. Stop and ask the user before running.")
    if int(preflight["missing_cache_count"]) > 0 and not bool(preflight["has_api_key"]):
        raise SystemExit("SHIELD_API_KEY is not set and required LLM cache entries are missing. No result directory was created.")
    return preflight


def warmup_llm_or_exit(backend_name: str, backend_module, planned_rows: list[dict[str, str]]) -> None:
    if backend_name != "llm" or not os.getenv("SHIELD_API_KEY"):
        return
    failures = 0
    checked = 0
    for row in planned_rows[:3]:
        result = backend_module.classify_comment(row["comment"], row.get("context", ""))
        checked += 1
        if getattr(result, "error_type", "") == "api_error":
            failures += 1
    if checked == 3 and failures == 3:
        raise SystemExit("First three LLM calls failed due to API/network/parse errors. No result directory was created.")


def run_backend(backend_name: str, jigsaw_n: int) -> None:
    backend = import_backend(backend_name)
    maybe_rename_context_columns(ROOT / "evals" / "context_eval_cases.csv")
    core_rows = load_core_rows()
    context_rows = read_csv(ROOT / "evals" / "context_eval_cases.csv")
    jigsaw_rows = read_csv(ROOT / "data" / "public_jigsaw_sample_300.csv")[:jigsaw_n] if jigsaw_n else []
    planned_rows = list(core_rows) + list(jigsaw_rows)
    planned_rows += [{"comment": row["final_comment"], "context": ""} for row in context_rows]
    planned_rows += [{"comment": row["final_comment"], "context": row["preceding_context"]} for row in context_rows]
    preflight = preflight_or_exit(backend_name, backend, planned_rows)
    warmup_llm_or_exit(backend_name, backend, planned_rows)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result_dir = ROOT / "evals" / "results" / f"{timestamp}_{backend_name}"
    latest_dir = ROOT / "evals" / "latest"
    result_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    core_outputs, core_metrics = evaluate_rows(core_rows, backend, backend_name)
    write_csv(latest_dir / f"{backend_name}_eval_cases.csv", core_outputs)
    write_csv(result_dir / "eval_cases.csv", core_outputs)

    context_outputs = evaluate_context(context_rows, backend, backend_name)
    write_csv(result_dir / "context_eval_results.csv", context_outputs)
    context_summary = context_metrics(context_outputs)

    lazy = lazy_baseline_metrics(core_rows)
    write_csv(result_dir / "confusion_matrix.csv", confusion_matrix([str(r["true_label"]) for r in core_outputs], [str(r["predicted_label"]) for r in core_outputs]), ["true_label"] + LABELS + ["abstain"])

    jigsaw_metrics = None
    if jigsaw_rows:
        jigsaw_outputs, base_jigsaw_metrics = evaluate_rows(jigsaw_rows, backend, backend_name)
        jigsaw_metrics = {**base_jigsaw_metrics, **jigsaw_extra_metrics(jigsaw_outputs)}
        write_csv(result_dir / "public_jigsaw_eval.csv", jigsaw_outputs)
        with (result_dir / "public_jigsaw_metrics.json").open("w", encoding="utf-8") as handle:
            json.dump(jigsaw_metrics, handle, indent=2)

    slice_metrics = {
        "original12": metrics_for_slice(core_outputs, "original12", lambda r: bool_text(r.get("tuned_on")) == "true"),
        "fresh": metrics_for_slice(core_outputs, "fresh", lambda r: bool_text(r.get("tuned_on")) != "true"),
        "combined": core_metrics,
    }
    rows = metric_rows(backend_name, slice_metrics, context_summary, lazy, jigsaw_metrics)
    write_csv(latest_dir / f"{backend_name}_metrics_summary.csv", rows, ["metric", "slice", "target", "result", "notes"])
    write_csv(result_dir / "metrics_summary.csv", rows, ["metric", "slice", "target", "result", "notes"])

    total_decisions = len(core_outputs) + len(context_outputs) * 2 + (int(jigsaw_metrics["n"]) if jigsaw_metrics else 0)
    api_error_count = int(core_metrics["api_error_count"]) + int(context_summary["api_error_count"]) + (int(jigsaw_metrics["api_error_count"]) if jigsaw_metrics else 0)
    abstain_by_model_count = int(core_metrics["abstain_by_model_count"]) + (int(jigsaw_metrics["abstain_by_model_count"]) if jigsaw_metrics else 0)
    valid_run = False if total_decisions and api_error_count / total_decisions > 0.05 else True
    token_source = "local_no_tokens" if backend_name == "keyword" else "provider_usage"
    if backend_name == "llm" and any(int(r.get("input_tokens") or 0) == 0 and int(r.get("output_tokens") or 0) == 0 for r in core_outputs):
        token_source = "missing_or_estimated"
        valid_run = False
    metadata = {
        "timestamp": timestamp,
        "backend": backend_name,
        "jigsaw_n": jigsaw_n,
        "model": preflight.get("model", ""),
        "model_tier": preflight.get("model_tier", ""),
        "base_url": preflight.get("base_url", ""),
        "prompt_version": preflight.get("prompt_version", ""),
        "valid_run": valid_run,
        "api_error_count": api_error_count,
        "abstain_by_model_count": abstain_by_model_count,
        "token_source": token_source,
        "preflight": preflight,
        "slice_metrics": slice_metrics,
        "core_metrics": core_metrics,
        "context_metrics": context_summary,
        "jigsaw_metrics": jigsaw_metrics,
        "lazy_baseline": lazy,
    }
    with (result_dir / "run_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    with (latest_dir / f"{backend_name}_run_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    print(json.dumps(metadata, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["keyword", "llm", "both"], default="keyword")
    parser.add_argument("--jigsaw-n", type=int, default=0)
    args = parser.parse_args()
    backends = ["keyword", "llm"] if args.backend == "both" else [args.backend]
    for backend_name in backends:
        run_backend(backend_name, args.jigsaw_n)


if __name__ == "__main__":
    main()
