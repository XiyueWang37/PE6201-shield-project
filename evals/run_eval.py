"""Reproducible evaluation runner for Shield.

The script evaluates either the keyword fallback or the LLM backend against the
small inspected core set, the context movement set, and an optional public
Jigsaw supplementary sample. It writes timestamped artifacts under
`evals/results/` and rewrites the top-level eval summary CSV files from actual
runtime outputs.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
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
}
FPR_CEILING = 0.15


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_label(label: str) -> str:
    label = (label or "").strip().lower()
    return label if label in LABELS else "abstain"


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


def evaluate_rows(rows: list[dict[str, str]], backend_module, backend_name: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    outputs: list[dict[str, object]] = []
    y_true: list[str] = []
    y_pred: list[str] = []
    start = time.time()
    for row in rows:
        result = classify(backend_module, backend_name, row["comment"], row.get("context", ""))
        true_label = normalize_label(row.get("shield_label") or row.get("shield_label_mapped") or row.get("true_label"))
        pred_label = normalize_label(result.severity)
        y_true.append(true_label)
        y_pred.append(pred_label)
        outputs.append(
            {
                "id": row.get("id") or row.get("sample_id"),
                "comment": row["comment"],
                "context": row.get("context", ""),
                "true_label": true_label,
                "predicted_label": pred_label,
                "policy_action": result.policy_action,
                "confidence": result.confidence,
                "is_normal_criticism": str(row.get("is_normal_criticism", true_label == "normal")).lower(),
                "is_high_or_critical": str(row.get("is_high_or_critical", true_label in {"high", "critical"})).lower(),
                "correct": pred_label == true_label,
                "abstain": bool(getattr(result, "abstain", False)),
                "input_tokens": int(getattr(result, "input_tokens", 0)),
                "output_tokens": int(getattr(result, "output_tokens", 0)),
                "rationale": result.rationale,
            }
        )
    elapsed = time.time() - start
    metrics = metric_summary(outputs, y_true, y_pred, elapsed)
    return outputs, metrics


def metric_summary(outputs: list[dict[str, object]], y_true: list[str], y_pred: list[str], elapsed: float) -> dict[str, object]:
    normal = [r for r in outputs if str(r["is_normal_criticism"]).lower() == "true"]
    high = [r for r in outputs if str(r["is_high_or_critical"]).lower() == "true"]
    fp = sum(1 for r in normal if positive_action(str(r["policy_action"])))
    fn = sum(1 for r in high if r["policy_action"] != "escalate_to_moderator")
    fpr = fp / len(normal) if normal else 0.0
    fnr = fn / len(high) if high else 0.0
    fpr_ci = clopper_pearson(fp, len(normal)) if normal else (0.0, 0.0)
    fnr_ci = clopper_pearson(fn, len(high)) if high else (0.0, 0.0)
    abstain = sum(1 for r in outputs if r["abstain"])
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
        "accuracy": sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true) if y_true else 0.0,
        "macro_f1": macro_f1(y_true, y_pred) if y_true else 0.0,
        "abstention_rate": abstain / len(outputs) if outputs else 0.0,
    }


def lazy_baseline_metrics(rows: list[dict[str, str]]) -> dict[str, object]:
    outputs = []
    for row in rows:
        true_label = normalize_label(row.get("shield_label") or row.get("shield_label_mapped") or row.get("true_label"))
        outputs.append(
            {
                "is_normal_criticism": str(row.get("is_normal_criticism", true_label == "normal")).lower(),
                "is_high_or_critical": str(row.get("is_high_or_critical", true_label in {"high", "critical"})).lower(),
                "policy_action": "escalate_to_moderator",
                "abstain": False,
            }
        )
    y_true = [normalize_label(row.get("shield_label") or row.get("shield_label_mapped") or row.get("true_label")) for row in rows]
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
                "backend": backend_name,
            }
        )
    return out


def context_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {"context_n": 0, "strict_accuracy": 0.0, "lenient_accuracy": 0.0, "missed_expected_changes": 0}
    return {
        "context_n": len(rows),
        "strict_accuracy": sum(bool(r["strict_correct"]) for r in rows) / len(rows),
        "lenient_accuracy": sum(bool(r["lenient_correct"]) for r in rows) / len(rows),
        "missed_expected_changes": sum(bool(r["missed_expected_change"]) for r in rows),
    }


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_metric_files(backend_name: str, core_metrics: dict[str, object], context_summary: dict[str, object], lazy: dict[str, object], result_dir: Path) -> None:
    rows = [
        {"metric": "backend", "target": "reported", "result": backend_name, "notes": "Evaluation backend."},
        {"metric": "false_negative_rate_high_critical", "target": "<10%", "result": format_pct(float(core_metrics["false_negative_rate"])), "notes": f"{core_metrics['false_negative_count']} of {core_metrics['high_critical_n']} high/critical cases were not escalated. 95% CI {format_pct(float(core_metrics['false_negative_ci_low']))}-{format_pct(float(core_metrics['false_negative_ci_high']))}."},
        {"metric": "false_positive_rate_normal_criticism", "target": "<15%", "result": format_pct(float(core_metrics["false_positive_rate"])), "notes": f"{core_metrics['false_positive_count']} of {core_metrics['normal_n']} normal criticism cases were prompted/escalated. PASS={core_metrics['false_positive_pass']}. 95% CI {format_pct(float(core_metrics['false_positive_ci_low']))}-{format_pct(float(core_metrics['false_positive_ci_high']))}."},
        {"metric": "overall_accuracy", "target": "reported", "result": format_pct(float(core_metrics["accuracy"])), "notes": "Exact severity match on the core set."},
        {"metric": "macro_f1", "target": "reported", "result": f"{float(core_metrics['macro_f1']):.3f}", "notes": "Macro F1 across severity labels."},
        {"metric": "abstention_rate", "target": "reported", "result": format_pct(float(core_metrics["abstention_rate"])), "notes": "Rate of backend abstention."},
        {"metric": "lazy_baseline_fnr_high_critical", "target": "critique", "result": format_pct(float(lazy["false_negative_rate"])), "notes": "All-high baseline shows FNR can be gamed."},
        {"metric": "lazy_baseline_fpr_normal_criticism", "target": "critique", "result": format_pct(float(lazy["false_positive_rate"])), "notes": "All-high baseline over-prompts all normal criticism."},
        {"metric": "context_strict_accuracy", "target": "reported", "result": format_pct(float(context_summary["strict_accuracy"])), "notes": f"Strict movement result over {context_summary['context_n']} context cases."},
        {"metric": "context_lenient_accuracy", "target": "reported", "result": format_pct(float(context_summary["lenient_accuracy"])), "notes": f"Lenient movement result; missed expected changes={context_summary['missed_expected_changes']}."},
    ]
    fieldnames = ["metric", "target", "result", "notes"]
    write_csv(ROOT / "evals" / "metrics_summary.csv", rows, fieldnames)
    write_csv(result_dir / "metrics_summary.csv", rows, fieldnames)


def maybe_rename_context_columns(path: Path) -> None:
    rows = read_csv(path)
    if not rows:
        return
    if "label_without_context" not in rows[0] and "label_with_context" not in rows[0]:
        return
    new_rows = []
    for row in rows:
        copied = dict(row)
        copied["legacy_handwritten_label_without_context"] = copied.pop("label_without_context", "")
        copied["legacy_handwritten_label_with_context"] = copied.pop("label_with_context", "")
        new_rows.append(copied)
    fieldnames = [
        "id",
        "preceding_context",
        "final_comment",
        "legacy_handwritten_label_without_context",
        "legacy_handwritten_label_with_context",
        "expected_movement",
        "correct",
        "notes",
    ]
    write_csv(path, new_rows, fieldnames)


def run_backend(backend_name: str, jigsaw_n: int) -> None:
    backend = import_backend(backend_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result_dir = ROOT / "evals" / "results" / f"{timestamp}_{backend_name}"
    result_dir.mkdir(parents=True, exist_ok=True)

    maybe_rename_context_columns(ROOT / "evals" / "context_eval_cases.csv")
    core_rows = read_csv(ROOT / "data" / "relabelled_eval_set.csv")
    context_rows = read_csv(ROOT / "evals" / "context_eval_cases.csv")

    core_outputs, core_metrics = evaluate_rows(core_rows, backend, backend_name)
    write_csv(ROOT / "evals" / "eval_cases.csv", core_outputs, list(core_outputs[0].keys()))
    write_csv(result_dir / "eval_cases.csv", core_outputs, list(core_outputs[0].keys()))

    context_outputs = evaluate_context(context_rows, backend, backend_name)
    write_csv(result_dir / "context_eval_results.csv", context_outputs, list(context_outputs[0].keys()))
    context_summary = context_metrics(context_outputs)

    lazy = lazy_baseline_metrics(core_rows)
    write_csv(result_dir / "confusion_matrix.csv", confusion_matrix([str(r["true_label"]) for r in core_outputs], [str(r["predicted_label"]) for r in core_outputs]), ["true_label"] + LABELS + ["abstain"])

    if jigsaw_n:
        jigsaw_rows = read_csv(ROOT / "data" / "public_jigsaw_sample_300.csv")[:jigsaw_n]
        jigsaw_outputs, jigsaw_metrics = evaluate_rows(jigsaw_rows, backend, backend_name)
        write_csv(result_dir / "public_jigsaw_eval.csv", jigsaw_outputs, list(jigsaw_outputs[0].keys()))
        with (result_dir / "public_jigsaw_metrics.json").open("w", encoding="utf-8") as handle:
            json.dump(jigsaw_metrics, handle, indent=2)

    write_metric_files(backend_name, core_metrics, context_summary, lazy, result_dir)
    metadata = {
        "timestamp": timestamp,
        "backend": backend_name,
        "jigsaw_n": jigsaw_n,
        "core_metrics": core_metrics,
        "context_metrics": context_summary,
        "lazy_baseline": lazy,
    }
    with (result_dir / "run_metadata.json").open("w", encoding="utf-8") as handle:
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
