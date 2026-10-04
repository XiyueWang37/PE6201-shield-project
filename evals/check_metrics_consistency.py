"""Check that documented headline metrics match reproducible results.

This lightweight checker compares the key numbers in `docs/metrics_summary.md`
and `docs/final_report_draft.md` with the latest committed keyword result and
cost report. It is intentionally conservative: it checks headline strings rather
than trying to parse every table cell.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYWORD_RUN = ROOT / "evals" / "results" / "20261004T082551Z_keyword" / "run_metadata.json"
COST_REPORT = ROOT / "evals" / "results" / "cost_report.csv"
DOCS = [ROOT / "docs" / "metrics_summary.md", ROOT / "docs" / "final_report_draft.md", ROOT / "README.md"]


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> int:
    metadata = json.loads(KEYWORD_RUN.read_text(encoding="utf-8"))
    metrics = metadata["core_metrics"]
    context = metadata["context_metrics"]
    expected = [
        pct(metrics["false_negative_rate"]),
        pct(metrics["false_positive_rate"]),
        pct(metrics["accuracy"]),
        f"{metrics['macro_f1']:.3f}",
        pct(context["strict_accuracy"]),
        "USD 55.56",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    missing = [item for item in expected if item not in combined]
    if missing:
        print("Metric consistency check failed. Missing documented values:")
        for item in missing:
            print(f"- {item}")
        return 1
    print("Metric consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
