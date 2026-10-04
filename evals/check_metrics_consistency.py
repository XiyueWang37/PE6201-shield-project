"""Check that documentation matches generated metric artifacts.

The checker fails on stale references to deleted or invalid result runs. It reads
`evals/latest/` and the newest valid timestamped result instead of hard-coding a
timestamp, then verifies that the key published values in the docs match those
artifacts.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "metrics_summary.md",
    ROOT / "docs" / "final_report_draft.md",
]
DELETED_OR_INVALID_REFS = [
    "20261004T082448Z_keyword",
    "20261004T082500Z_llm",
    "USD 666.70",
    "USD 55.56",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def latest_valid_metadata(backend: str) -> tuple[Path, dict[str, object]]:
    candidates = sorted(
        path
        for path in (ROOT / "evals" / "results").glob("20*T*_*/*")
        if path.name == "run_metadata.json"
    )
    valid = []
    for path in candidates:
        with path.open(encoding="utf-8") as handle:
            metadata = json.load(handle)
        if metadata.get("backend") == backend and metadata.get("valid_run") is True:
            valid.append((path.parent, metadata))
    if not valid:
        raise FileNotFoundError(f"No valid {backend} result found")
    return valid[-1]


def doc_lines() -> dict[Path, list[str]]:
    return {path: path.read_text(encoding="utf-8").splitlines() for path in DOCS}


def find_stale_references(lines_by_doc: dict[Path, list[str]]) -> list[str]:
    errors = []
    for path, lines in lines_by_doc.items():
        for line_no, line in enumerate(lines, start=1):
            for needle in DELETED_OR_INVALID_REFS:
                if needle in line:
                    errors.append(f"{path.relative_to(ROOT)}:{line_no}: stale or invalid reference `{needle}`")
            for match in re.findall(r"evals/results/(20\d{6}T\d{6}Z_[A-Za-z0-9_]+)", line):
                metadata = ROOT / "evals" / "results" / match / "run_metadata.json"
                if not metadata.exists():
                    errors.append(f"{path.relative_to(ROOT)}:{line_no}: references missing result directory `{match}`")
                else:
                    data = json.loads(metadata.read_text(encoding="utf-8"))
                    if data.get("valid_run") is not True:
                        errors.append(f"{path.relative_to(ROOT)}:{line_no}: references valid_run=false result `{match}`")
    return errors


def rows_by_metric(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    return {(row["slice"], row["metric"]): row for row in read_csv(path)}


def metric_result(path: Path, slice_name: str, metric: str) -> str:
    rows = rows_by_metric(path)
    try:
        return rows[(slice_name, metric)]["result"]
    except KeyError as exc:
        raise KeyError(f"Missing {slice_name}/{metric} in {path}") from exc


def cost_row(backend: str) -> dict[str, str]:
    for row in read_csv(ROOT / "evals" / "results" / "cost_report.csv"):
        if row["backend"] == backend and row["prevalence_scenario"] == "platform_assumed":
            return row
    raise KeyError(f"Missing platform_assumed cost row for {backend}")


def expected_strings() -> list[str]:
    keyword = ROOT / "evals" / "latest" / "keyword_metrics_summary.csv"
    llm = ROOT / "evals" / "latest" / "llm_metrics_summary.csv"
    wanted = [
        metric_result(keyword, "fresh", "false_negative_rate_high_critical"),
        metric_result(keyword, "fresh", "false_positive_rate_normal_criticism"),
        metric_result(keyword, "fresh", "action_accuracy"),
        metric_result(keyword, "fresh", "overall_accuracy"),
        metric_result(keyword, "fresh", "macro_f1"),
        metric_result(keyword, "context", "context_strict_accuracy"),
        metric_result(llm, "fresh", "false_negative_rate_high_critical"),
        metric_result(llm, "fresh", "false_positive_rate_normal_criticism"),
        metric_result(llm, "fresh", "action_accuracy"),
        metric_result(llm, "fresh", "overall_accuracy"),
        metric_result(llm, "fresh", "macro_f1"),
        metric_result(llm, "context", "context_strict_accuracy"),
        metric_result(llm, "context", "context_lenient_accuracy"),
        metric_result(keyword, "public_jigsaw", "jigsaw_threat_flagged_fnr"),
        metric_result(llm, "public_jigsaw", "jigsaw_threat_flagged_fnr"),
    ]
    for backend in ("keyword", "llm"):
        row = cost_row(backend)
        wanted.append(f"USD {float(row['total_cost_per_1000_comments']):.2f}")
        if backend == "llm":
            wanted.append(f"USD {float(row['token_cost_per_1000_comments']):.6f}")
        wanted.append(row["p_action_success"])
    return sorted(set(item for item in wanted if item))


def main() -> int:
    latest_valid_metadata("keyword")
    latest_valid_metadata("llm")
    lines_by_doc = doc_lines()
    errors = find_stale_references(lines_by_doc)
    combined = "\n".join("\n".join(lines) for lines in lines_by_doc.values())
    for item in expected_strings():
        if item not in combined:
            errors.append(f"documented metric string missing from docs: `{item}`")
    if errors:
        print("Metric consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Metric consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
