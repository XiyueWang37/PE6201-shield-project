"""Merge confirmed candidate labels into evaluation inputs.

This script does not edit `data/candidates_to_label.csv` or
`data/relabelled_eval_set.csv`. It writes derived evaluation files:

- `data/core_eval_set.csv` for single-comment severity evaluation.
- `evals/context_eval_cases.csv` with the original context cases plus confirmed
  thread candidates.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID = {"normal", "low", "medium", "high", "critical"}
CORE_FIELDS = [
    "id",
    "source",
    "comment",
    "context",
    "shield_label",
    "is_normal_criticism",
    "is_high_or_critical",
    "hard_case_type",
    "tuned_on",
]
CONTEXT_FIELDS = [
    "id",
    "preceding_context",
    "final_comment",
    "legacy_handwritten_label_without_context",
    "legacy_handwritten_label_with_context",
    "expected_movement",
    "correct",
    "notes",
    "source",
    "shield_label",
    "label_alone",
    "review_status",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def validate_candidates(rows: list[dict[str, str]]) -> None:
    blank = [row["id"] for row in rows if not row.get("shield_label", "").strip()]
    if blank:
        raise SystemExit(f"Blank shield_label rows remain: {', '.join(blank)}")
    invalid = [(row["id"], row.get("shield_label", "")) for row in rows if row.get("shield_label", "").strip().lower() not in VALID]
    if invalid:
        raise SystemExit(f"Invalid labels: {invalid}")
    unconfirmed_threads = [
        row["id"]
        for row in rows
        if row.get("candidate_type") == "thread"
        and (not row.get("label_alone") or not row.get("expected_movement") or row.get("review_status") != "confirmed_by_user_from_draft")
    ]
    if unconfirmed_threads:
        raise SystemExit(f"Unconfirmed thread rows: {', '.join(unconfirmed_threads)}")


def original_core_rows() -> list[dict[str, object]]:
    rows = []
    for row in read_csv(ROOT / "data" / "relabelled_eval_set.csv"):
        label = row["shield_label"].strip().lower()
        rows.append(
            {
                "id": f"orig_{row['id']}",
                "source": "manual_original",
                "comment": row["comment"],
                "context": row.get("context", ""),
                "shield_label": label,
                "is_normal_criticism": bool_text(label == "normal"),
                "is_high_or_critical": bool_text(label in {"high", "critical"}),
                "hard_case_type": "original_tuned_case",
                "tuned_on": "true",
            }
        )
    return rows


def candidate_single_rows(candidates: list[dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for row in candidates:
        if row["candidate_type"] != "single":
            continue
        label = row["shield_label"].strip().lower()
        rows.append(
            {
                "id": f"cand_{row['id']}",
                "source": "ai_drafted_human_reviewed",
                "comment": row["comment"],
                "context": "",
                "shield_label": label,
                "is_normal_criticism": bool_text(label == "normal"),
                "is_high_or_critical": bool_text(label in {"high", "critical"}),
                "hard_case_type": row.get("hard_case_type", ""),
                "tuned_on": "false",
            }
        )
    return rows


def context_rows(candidates: list[dict[str, str]]) -> list[dict[str, object]]:
    base = []
    for row in read_csv(ROOT / "evals" / "context_eval_cases.csv"):
        if row.get("source") == "ai_drafted_human_reviewed":
            continue
        copied = {field: row.get(field, "") for field in CONTEXT_FIELDS}
        copied["source"] = copied.get("source") or "manual_original"
        copied["shield_label"] = copied.get("shield_label") or copied.get("legacy_handwritten_label_with_context", "")
        copied["label_alone"] = copied.get("label_alone") or copied.get("legacy_handwritten_label_without_context", "")
        copied["review_status"] = copied.get("review_status") or "original_context_case"
        base.append(copied)
    for row in candidates:
        if row["candidate_type"] != "thread":
            continue
        base.append(
            {
                "id": f"cand_{row['id']}",
                "preceding_context": row["preceding_context"],
                "final_comment": row["final_comment"],
                "legacy_handwritten_label_without_context": "",
                "legacy_handwritten_label_with_context": "",
                "expected_movement": row["expected_movement"],
                "correct": "",
                "notes": row.get("notes", ""),
                "source": "ai_drafted_human_reviewed",
                "shield_label": row["shield_label"].strip().lower(),
                "label_alone": row["label_alone"].strip().lower(),
                "review_status": row.get("review_status", ""),
            }
        )
    return base


def main() -> int:
    candidates = read_csv(ROOT / "data" / "candidates_to_label.csv")
    validate_candidates(candidates)
    core = original_core_rows() + candidate_single_rows(candidates)
    contexts = context_rows(candidates)
    write_csv(ROOT / "data" / "core_eval_set.csv", core, CORE_FIELDS)
    write_csv(ROOT / "evals" / "context_eval_cases.csv", contexts, CONTEXT_FIELDS)

    fresh = [row for row in core if row["tuned_on"] == "false"]
    high_critical = sum(row["shield_label"] in {"high", "critical"} for row in fresh)
    normal = sum(row["shield_label"] == "normal" for row in fresh)
    hard_normal = sum(row["shield_label"] == "normal" and row["hard_case_type"] in {"non_targeted_profanity", "sarcasm", "idea_targeted_insult"} for row in fresh)
    thread_count = sum(row["source"] == "ai_drafted_human_reviewed" for row in contexts)
    counts = {
        "core_total": len(core),
        "original12": len([row for row in core if row["tuned_on"] == "true"]),
        "fresh_single": len(fresh),
        "fresh_label_counts": dict(Counter(row["shield_label"] for row in fresh)),
        "fresh_high_critical": high_critical,
        "target_high_critical_ge_30": high_critical >= 30,
        "fresh_normal_criticism": normal,
        "target_normal_ge_30": normal >= 30,
        "hard_normal_count": hard_normal,
        "confirmed_threads": thread_count,
        "target_threads_15_to_20": 15 <= len(contexts) <= 20,
        "context_total": len(contexts),
    }
    for key, value in counts.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
