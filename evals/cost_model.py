"""Platform-scale cost model for Shield moderation.

Formula from the course Class 5 frame:

    cost per task = token_cost + (1 - p) * fallback_cost

where p is the probability that the predicted policy action equals the gold
policy action and the classifier does not abstain. Correct escalation of truly
high-risk comments is a necessary review load, not a model failure.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals" / "results"
LATEST = ROOT / "evals" / "latest"
OUT_DIR = RESULTS
LABELS = ["normal", "low", "medium", "high", "critical"]
GOLD_ACTION = {
    "normal": "allow",
    "low": "allow",
    "medium": "prompt_reconsider",
    "high": "escalate_to_moderator",
    "critical": "escalate_to_moderator",
}

CONFIG = {
    "currency": "USD",
    "price_date": "2026-10-04",
    "price_source_note": "ASSUMED values for course prototype; verify against provider price pages before submission.",
    "models": {
        "cheap_assumed": {
            "model_id": "openai/gpt-4o-mini",
            "input_per_million": 0.15,
            "output_per_million": 0.60,
        },
        "frontier_assumed": {
            "model_id": "not_chosen_not_measured",
            "input_per_million": 5.00,
            "output_per_million": 15.00,
            "measured": False,
        },
        "local_rules": {
            "model_id": "keyword_local",
            "input_per_million": 0.0,
            "output_per_million": 0.0,
        },
    },
    "manual_review_minutes": 2.0,
    "manual_reviewer_hourly_cost": 20.0,
    "monthly_comment_volume": 1_000_000,
    "platform_prevalence": {
        "normal": 0.96,
        "low": 0.00,
        "medium": 0.03,
        "high": 0.007,
        "critical": 0.003,
    },
    "severe_prevalence_scenarios": [0.005, 0.01, 0.05],
    "missed_severe_harm_cost": 0.0,
    "missed_severe_harm_cost_note": "ASSUMED 0; severe-miss harm is reported as risk, not modelled in the main cost.",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def assert_config() -> None:
    assert CONFIG["currency"] == "USD"
    assert CONFIG["manual_review_minutes"] >= 0
    assert CONFIG["manual_reviewer_hourly_cost"] >= 0
    assert CONFIG["monthly_comment_volume"] > 0
    prevalence_sum = sum(CONFIG["platform_prevalence"].values())
    assert abs(prevalence_sum - 1.0) < 1e-9
    for model in CONFIG["models"].values():
        assert model["input_per_million"] >= 0
        assert model["output_per_million"] >= 0


def latest_metadata_paths(results_dir: Path = RESULTS) -> list[Path]:
    paths = sorted(results_dir.glob("*_* /run_metadata.json"))
    if not paths:
        paths = sorted(results_dir.glob("*_*/*"))
    return sorted(results_dir.glob("20*T*_* /run_metadata.json"))


def find_run_metadata(results_dir: Path = RESULTS) -> list[Path]:
    return sorted(path for path in results_dir.glob("20*T*_*/*") if path.name == "run_metadata.json")


def latest_valid_run(backend: str, results_dir: Path = RESULTS) -> tuple[Path, dict[str, object]] | None:
    candidates = []
    for metadata_path in find_run_metadata(results_dir):
        with metadata_path.open(encoding="utf-8") as handle:
            metadata = json.load(handle)
        if metadata.get("backend") == backend:
            candidates.append((metadata_path.parent, metadata))
    for result_dir, metadata in reversed(candidates):
        if metadata.get("valid_run") is True:
            return result_dir, metadata
    return None


def manual_review_cost() -> float:
    return CONFIG["manual_review_minutes"] / 60 * CONFIG["manual_reviewer_hourly_cost"]


def model_for_run(metadata: dict[str, object]) -> tuple[str, dict[str, object]]:
    backend = metadata.get("backend")
    if backend == "keyword":
        return "local_rules", CONFIG["models"]["local_rules"]
    model_id = str(metadata.get("model", ""))
    tier = str(metadata.get("model_tier", ""))
    if tier in CONFIG["models"] and CONFIG["models"][tier]["model_id"] == model_id:
        return tier, CONFIG["models"][tier]
    for candidate_tier, model in CONFIG["models"].items():
        if model["model_id"] == model_id:
            return candidate_tier, model
    raise ValueError(f"No CONFIG model tier matches measured model: {model_id}")


def validate_run(metadata: dict[str, object]) -> None:
    if metadata.get("valid_run") is not True:
        raise ValueError("Cost model refuses valid_run=false results")
    backend = metadata.get("backend")
    token_source = metadata.get("token_source")
    if backend == "keyword":
        if token_source != "local_no_tokens":
            raise ValueError("Keyword token source must be local_no_tokens")
    elif token_source != "provider_usage":
        raise ValueError("LLM cost requires provider_usage tokens, not estimated or missing tokens")



def relative_result_dir(result_dir: Path) -> str:
    try:
        return str(result_dir.resolve().relative_to(ROOT))
    except ValueError:
        return str(result_dir)

def measured_rates(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    by_label: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_label[row["true_label"]].append(row)
    rates: dict[str, dict[str, float]] = {}
    for label in LABELS:
        subset = by_label.get(label, [])
        n = len(subset)
        if not n:
            rates[label] = {
                "n": 0,
                "p": 0.0,
                "necessary_review_load": 0.0,
                "false_positive_escalation": 0.0,
                "false_negative": 0.0,
                "avg_input_tokens": 0.0,
                "avg_output_tokens": 0.0,
            }
            continue
        gold = GOLD_ACTION[label]
        action_correct = [row for row in subset if row.get("action_correct") == "True" or row.get("action_correct") == "true"]
        necessary = [row for row in subset if gold == "escalate_to_moderator" and row.get("policy_action") == "escalate_to_moderator" and row in action_correct]
        false_positive_escalation = [row for row in subset if gold != "escalate_to_moderator" and row.get("policy_action") == "escalate_to_moderator"]
        false_negative = [row for row in subset if gold == "escalate_to_moderator" and row.get("policy_action") != "escalate_to_moderator"]
        rates[label] = {
            "n": n,
            "p": len(action_correct) / n,
            "necessary_review_load": len(necessary) / n,
            "false_positive_escalation": len(false_positive_escalation) / n,
            "false_negative": len(false_negative) / n,
            "avg_input_tokens": sum(float(row.get("input_tokens") or 0) for row in subset) / n,
            "avg_output_tokens": sum(float(row.get("output_tokens") or 0) for row in subset) / n,
        }
    return rates


def reweighted_value(rates: dict[str, dict[str, float]], prevalence: dict[str, float], field: str) -> float:
    return sum(prevalence[label] * rates[label][field] for label in LABELS)


def token_cost(avg_input: float, avg_output: float, model: dict[str, object]) -> float:
    cost = avg_input * float(model["input_per_million"]) / 1_000_000 + avg_output * float(model["output_per_million"]) / 1_000_000
    assert cost >= 0
    return cost


def scenario_for_prevalence(backend: str, result_dir: Path, metadata: dict[str, object], rows: list[dict[str, str]], prevalence_name: str, prevalence: dict[str, float]) -> dict[str, object]:
    validate_run(metadata)
    tier, model = model_for_run(metadata)
    rates = measured_rates(rows)
    p = reweighted_value(rates, prevalence, "p")
    assert 0 <= p <= 1
    avg_input = reweighted_value(rates, prevalence, "avg_input_tokens")
    avg_output = reweighted_value(rates, prevalence, "avg_output_tokens")
    per_task_token = token_cost(avg_input, avg_output, model)
    fallback = manual_review_cost()
    fallback_component = (1 - p) * fallback
    total = per_task_token + fallback_component
    assert total >= 0
    necessary_review = reweighted_value(rates, prevalence, "necessary_review_load") * 1000
    false_positive = reweighted_value(rates, prevalence, "false_positive_escalation")
    false_negative = reweighted_value(rates, prevalence, "false_negative")
    return {
        "backend": backend,
        "model_tier": tier,
        "model_id": model["model_id"],
        "prevalence_scenario": prevalence_name,
        "currency": CONFIG["currency"],
        "p_action_success": round(p, 6),
        "avg_input_tokens": round(avg_input, 3),
        "avg_output_tokens": round(avg_output, 3),
        "token_cost_per_1000_comments": round(per_task_token * 1000, 6),
        "expected_fallback_cost_per_1000_comments": round(fallback_component * 1000, 6),
        "total_cost_per_1000_comments": round(total * 1000, 6),
        "total_cost_per_1000_successful_decisions": "inf" if p == 0 else round((total * 1000) / p, 6),
        "necessary_review_load_per_1000": round(necessary_review, 3),
        "false_positive_escalation_rate": round(false_positive, 6),
        "false_negative_rate": round(false_negative, 6),
        "missed_severe_harm_cost_modelled": CONFIG["missed_severe_harm_cost"],
        "monthly_cost_at_config_volume": round(total * CONFIG["monthly_comment_volume"], 2),
        "source_result_dir": relative_result_dir(result_dir),
    }


def prevalence_with_severe(severe_rate: float) -> dict[str, float]:
    medium = CONFIG["platform_prevalence"]["medium"]
    high = severe_rate * 0.7
    critical = severe_rate * 0.3
    normal = 1 - medium - high - critical
    return {"normal": normal, "low": 0.0, "medium": medium, "high": high, "critical": critical}


def build_rows(results_dir: Path = RESULTS) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for backend in ["keyword", "llm"]:
        selected = latest_valid_run(backend, results_dir)
        if not selected:
            continue
        result_dir, metadata = selected
        eval_rows = read_csv(result_dir / "eval_cases.csv")
        rows.append(scenario_for_prevalence(backend, result_dir, metadata, eval_rows, "platform_assumed", CONFIG["platform_prevalence"]))
        observed_counts = defaultdict(int)
        for row in eval_rows:
            observed_counts[row["true_label"]] += 1
        observed_total = sum(observed_counts.values())
        observed = {label: observed_counts[label] / observed_total for label in LABELS}
        rows.append(scenario_for_prevalence(backend, result_dir, metadata, eval_rows, "eval_observed_reference_only", observed))
    return rows


def build_sensitivity(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    fallback = manual_review_cost()
    for row in rows:
        if row["prevalence_scenario"] != "platform_assumed":
            continue
        token_per_1000 = float(row["token_cost_per_1000_comments"])
        p = float(row["p_action_success"])
        for delta in [-0.10, 0.0, 0.10]:
            adjusted = min(1.0, max(0.0, p + delta))
            total = token_per_1000 + (1 - adjusted) * fallback * 1000
            out.append({"backend": row["backend"], "model_tier": row["model_tier"], "scenario": "p_delta", "value": delta, "adjusted_p": round(adjusted, 6), "total_cost_per_1000_comments": round(total, 6)})
    return out


def build_prevalence_sensitivity(results_dir: Path = RESULTS) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for backend in ["keyword", "llm"]:
        selected = latest_valid_run(backend, results_dir)
        if not selected:
            continue
        result_dir, metadata = selected
        eval_rows = read_csv(result_dir / "eval_cases.csv")
        for severe_rate in CONFIG["severe_prevalence_scenarios"]:
            scenario = scenario_for_prevalence(backend, result_dir, metadata, eval_rows, f"severe_{severe_rate:.3f}", prevalence_with_severe(severe_rate))
            out.append({"backend": backend, "model_tier": scenario["model_tier"], "severe_prevalence": severe_rate, "p_action_success": scenario["p_action_success"], "total_cost_per_1000_comments": scenario["total_cost_per_1000_comments"], "necessary_review_load_per_1000": scenario["necessary_review_load_per_1000"]})
    return out


def unmeasured_tiers(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    measured = {str(row["model_tier"]) for row in rows if row["prevalence_scenario"] == "platform_assumed"}
    out = []
    for tier, model in CONFIG["models"].items():
        if tier == "local_rules":
            continue
        if tier not in measured:
            out.append(
                {
                    "model_tier": tier,
                    "model_id": model["model_id"],
                    "status": "not measured",
                    "reason": "No valid run for this tier; excluded from scenario table and no p reused from another tier.",
                }
            )
    return out


def break_even(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    cheap = next((r for r in rows if r["model_tier"] == "cheap_assumed" and r["prevalence_scenario"] == "platform_assumed"), None)
    if not cheap:
        return []
    frontier_model = CONFIG["models"].get("frontier_assumed")
    if not frontier_model:
        return []
    fallback = manual_review_cost()
    if fallback <= 0:
        return []
    cheap_total_per_task = float(cheap["total_cost_per_1000_comments"]) / 1000
    frontier_token_per_task = token_cost(float(cheap["avg_input_tokens"]), float(cheap["avg_output_tokens"]), frontier_model)
    p_star = 1 - (cheap_total_per_task - frontier_token_per_task) / fallback
    return [
        {
            "baseline": "cheap_assumed",
            "candidate": "frontier_assumed",
            "required_frontier_p": round(p_star, 6),
            "observed_cheap_p": cheap["p_action_success"],
            "observed_frontier_p": "not measured",
            "frontier_token_cost_assumption": "uses cheap measured token volume with frontier ASSUMED token prices",
            "conclusion": "No frontier result was measured; do not claim frontier wins or loses.",
        }
    ]


def write_report(rows: list[dict[str, object]], break_even_rows: list[dict[str, object]]) -> None:
    lines = [
        "# Shield Cost Report",
        "",
        f"Currency: {CONFIG['currency']}",
        f"Price date: {CONFIG['price_date']}",
        f"Price source note: {CONFIG['price_source_note']}",
        f"Missed severe harm cost: {CONFIG['missed_severe_harm_cost_note']}",
        "",
        "All prices, review time, review wages, monthly volume, prevalence, and harm-cost values are ASSUMED and must be verified before submission.",
        "",
        "## Scenario Results",
        "",
        "| Backend | Model tier | Prevalence | p | Token cost / 1,000 | Fallback cost / 1,000 | Total / 1,000 | Necessary review / 1,000 | FN rate |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| {row['backend']} | {row['model_tier']} | {row['prevalence_scenario']} | {row['p_action_success']} | {row['token_cost_per_1000_comments']} | {row['expected_fallback_cost_per_1000_comments']} | {row['total_cost_per_1000_comments']} | {row['necessary_review_load_per_1000']} | {row['false_negative_rate']} |")
    lines += ["", "## Break-even", ""]
    if break_even_rows:
        for row in break_even_rows:
            lines.append(
                f"Frontier required p*: {row['required_frontier_p']}; observed cheap p: {row['observed_cheap_p']}; "
                f"observed frontier p: {row['observed_frontier_p']}. {row['conclusion']}"
            )
            lines.append(f"Note: {row['frontier_token_cost_assumption']}.")
    else:
        lines.append("Break-even was not computed because no valid cheap LLM run is available.")
    lines += ["", "## Unmeasured Tiers", ""]
    unmeasured = unmeasured_tiers(rows)
    if unmeasured:
        for item in unmeasured:
            lines.append(f"- {item['model_tier']} ({item['model_id']}): {item['status']}. {item['reason']}")
    else:
        lines.append("No unmeasured configured LLM tiers.")
    lines += ["", "See `cost_sensitivity.csv` and `cost_prevalence_sensitivity.csv` for sensitivity tables."]
    (OUT_DIR / "cost_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    assert_config()
    rows = build_rows()
    if not rows:
        raise SystemExit("No valid result runs found for cost modelling.")
    write_csv(OUT_DIR / "cost_report.csv", rows)
    write_csv(OUT_DIR / "cost_sensitivity.csv", build_sensitivity(rows))
    prevalence_rows = build_prevalence_sensitivity()
    if prevalence_rows:
        write_csv(OUT_DIR / "cost_prevalence_sensitivity.csv", prevalence_rows)
    unmeasured = unmeasured_tiers(rows)
    if unmeasured:
        write_csv(OUT_DIR / "cost_unmeasured_tiers.csv", unmeasured)
    be_rows = break_even(rows)
    if be_rows:
        write_csv(OUT_DIR / "cost_break_even.csv", be_rows)
    write_report(rows, be_rows)
    print(f"Wrote {OUT_DIR / 'cost_report.md'}")


if __name__ == "__main__":
    main()
