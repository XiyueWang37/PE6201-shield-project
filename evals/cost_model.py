"""Cost model for Shield moderation decisions.

The model reads measured evaluation outputs from `evals/results/`, applies
ASSUMED token and human-review prices, and writes a reproducible cost report.
All prices in CONFIG must be verified by the user against provider price pages
before final submission.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals" / "results"
OUT_DIR = RESULTS

CONFIG = {
    "currency": "USD",
    "price_date": "2026-10-04",
    "price_source_note": "ASSUMED values for course prototype; verify against provider price pages before submission.",
    "models": {
        "cheap_assumed": {"input_per_million": 0.15, "output_per_million": 0.60},
        "frontier_assumed": {"input_per_million": 5.00, "output_per_million": 15.00},
    },
    "manual_review_minutes": 2.0,
    "manual_reviewer_hourly_cost": 20.0,
    "monthly_comment_volume": 1_000_000,
    "monthly_eval_runs": 4,
    "monthly_eval_comments_per_run": 300,
    "monthly_monitoring_fixed_cost": 100.0,
    "monthly_engineer_fraction_cost": 500.0,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def latest_result_dir(backend: str) -> Path:
    matches = sorted(RESULTS.glob(f"*_{backend}"))
    if not matches:
        raise FileNotFoundError(f"No result directory found for backend {backend}")
    return matches[-1]


def load_backend_rows(backend: str) -> tuple[Path, list[dict[str, str]], dict[str, object]]:
    result_dir = latest_result_dir(backend)
    rows = read_csv(result_dir / "eval_cases.csv")
    with (result_dir / "run_metadata.json").open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    return result_dir, rows, metadata


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def backend_stats(backend: str) -> dict[str, float | str]:
    result_dir, rows, metadata = load_backend_rows(backend)
    input_tokens = [float(row.get("input_tokens") or 0) for row in rows]
    output_tokens = [float(row.get("output_tokens") or 0) for row in rows]
    escalated = [idx for idx, row in enumerate(rows) if row.get("policy_action") == "escalate_to_moderator"]
    abstained = [idx for idx, row in enumerate(rows) if str(row.get("abstain", "")).lower() == "true"]
    fallback_indices = set(escalated) | set(abstained)
    fallback_rate = len(fallback_indices) / len(rows) if rows else 0.0
    success_rate = 1.0 - fallback_rate
    assert 0 <= success_rate <= 1
    return {
        "backend": backend,
        "result_dir": str(result_dir.relative_to(ROOT)),
        "n": float(len(rows)),
        "avg_input_tokens": mean(input_tokens),
        "avg_output_tokens": mean(output_tokens),
        "escalate_rate": len(escalated) / len(rows) if rows else 0.0,
        "abstention_rate": len(abstained) / len(rows) if rows else 0.0,
        "fallback_rate": fallback_rate,
        "success_rate": success_rate,
    }


def token_cost_per_comment(stats: dict[str, float | str], model: dict[str, float]) -> float:
    assert model["input_per_million"] > 0
    assert model["output_per_million"] > 0
    return (
        float(stats["avg_input_tokens"]) * model["input_per_million"] / 1_000_000
        + float(stats["avg_output_tokens"]) * model["output_per_million"] / 1_000_000
    )


def manual_review_cost_per_comment(stats: dict[str, float | str]) -> float:
    minutes = CONFIG["manual_review_minutes"]
    hourly = CONFIG["manual_reviewer_hourly_cost"]
    assert minutes >= 0 and hourly >= 0
    per_review = minutes / 60 * hourly
    return float(stats["fallback_rate"]) * per_review


def fixed_monthly_cost() -> float:
    monitoring = CONFIG["monthly_monitoring_fixed_cost"]
    engineering = CONFIG["monthly_engineer_fraction_cost"]
    assert monitoring >= 0 and engineering >= 0
    return monitoring + engineering


def scenario_rows() -> list[dict[str, object]]:
    rows = []
    for backend in ["keyword", "llm"]:
        try:
            stats = backend_stats(backend)
        except FileNotFoundError:
            continue
        for model_name, model in CONFIG["models"].items():
            token_cost = token_cost_per_comment(stats, model)
            review_cost = manual_review_cost_per_comment(stats)
            variable_cost = token_cost + review_cost
            per_1000_comments = variable_cost * 1000
            success_rate = float(stats["success_rate"])
            per_1000_success = per_1000_comments / success_rate if success_rate > 0 else float("inf")
            monthly = variable_cost * CONFIG["monthly_comment_volume"] + fixed_monthly_cost()
            assert token_cost >= 0 and review_cost >= 0 and monthly >= 0
            rows.append(
                {
                    "backend": backend,
                    "model_tier": model_name,
                    "currency": CONFIG["currency"],
                    "avg_input_tokens": round(float(stats["avg_input_tokens"]), 3),
                    "avg_output_tokens": round(float(stats["avg_output_tokens"]), 3),
                    "success_rate": round(success_rate, 4),
                    "escalate_rate": round(float(stats["escalate_rate"]), 4),
                    "abstention_rate": round(float(stats["abstention_rate"]), 4),
                    "token_cost_per_1000_comments": round(token_cost * 1000, 6),
                    "expected_review_cost_per_1000_comments": round(review_cost * 1000, 6),
                    "total_cost_per_1000_comments": round(per_1000_comments, 6),
                    "total_cost_per_1000_successful_decisions": "inf" if per_1000_success == float("inf") else round(per_1000_success, 6),
                    "monthly_cost_at_config_volume": round(monthly, 2),
                    "source_result_dir": stats["result_dir"],
                }
            )
    return rows


def sensitivity_rows(base_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for row in base_rows:
        total = float(row["total_cost_per_1000_comments"])
        success = float(row["success_rate"])
        for delta in [-0.10, 0.0, 0.10]:
            adjusted = min(1.0, max(0.0, success + delta))
            rows.append(
                {
                    "backend": row["backend"],
                    "model_tier": row["model_tier"],
                    "success_rate_adjustment": delta,
                    "adjusted_success_rate": round(adjusted, 4),
                    "cost_per_1000_successful_decisions": "inf" if adjusted == 0 else round(total / adjusted, 6),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict[str, object]], sensitivity: list[dict[str, object]]) -> None:
    lines = [
        "# Shield Cost Report",
        "",
        f"Currency: {CONFIG['currency']}",
        f"Price date: {CONFIG['price_date']}",
        f"Price source note: {CONFIG['price_source_note']}",
        "",
        "All model prices and human-review costs are ASSUMED and must be verified by the user against provider price pages before submission.",
        "",
        "## Scenario Results",
        "",
        "| Backend | Model tier | Cost / 1,000 comments | Cost / 1,000 successful decisions | Monthly cost | Success rate | Escalate rate | Abstention rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['backend']} | {row['model_tier']} | {row['total_cost_per_1000_comments']} | "
            f"{row['total_cost_per_1000_successful_decisions']} | {row['monthly_cost_at_config_volume']} | "
            f"{row['success_rate']} | {row['escalate_rate']} | {row['abstention_rate']} |"
        )
    lines += [
        "",
        "## Break-even Note",
        "",
        "The cheap and frontier token tiers have the same observed success rate within a backend unless real LLM measurements are added. Break-even therefore depends on the frontier model improving success enough to offset its higher token price and any reduction in human review fallback.",
        "",
        "## Sensitivity",
        "",
        "See `cost_sensitivity.csv` for success-rate +/-10 percentage point scenarios.",
    ]
    (OUT_DIR / "cost_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    assert CONFIG["currency"] == "USD"
    rows = scenario_rows()
    write_csv(OUT_DIR / "cost_report.csv", rows)
    sensitivity = sensitivity_rows(rows)
    write_csv(OUT_DIR / "cost_sensitivity.csv", sensitivity)
    write_report(rows, sensitivity)
    print(f"Wrote {OUT_DIR / 'cost_report.md'}")


if __name__ == "__main__":
    main()
