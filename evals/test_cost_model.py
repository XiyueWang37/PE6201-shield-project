"""Unit tests for the Shield cost model."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cost_model


META = {
    "backend": "keyword",
    "valid_run": True,
    "token_source": "local_no_tokens",
    "model": "keyword_local",
    "model_tier": "local_rules",
}


def row(label: str, action: str, correct: bool) -> dict[str, str]:
    return {
        "true_label": label,
        "policy_action": action,
        "action_correct": str(correct),
        "input_tokens": "0",
        "output_tokens": "0",
    }


class CostModelTests(unittest.TestCase):
    def test_fewer_false_negatives_cost_no_more_with_same_tokens(self) -> None:
        prevalence = {"normal": 0.0, "low": 0.0, "medium": 0.0, "high": 1.0, "critical": 0.0}
        worse = [row("high", "allow", False)]
        better = [row("high", "escalate_to_moderator", True)]
        worse_result = cost_model.scenario_for_prevalence("keyword", Path("evals/results/worse_keyword"), META, worse, "test", prevalence)
        better_result = cost_model.scenario_for_prevalence("keyword", Path("evals/results/better_keyword"), META, better, "test", prevalence)
        self.assertLessEqual(float(better_result["total_cost_per_1000_comments"]), float(worse_result["total_cost_per_1000_comments"]))

    def test_correct_escalation_is_necessary_load_not_failure_cost(self) -> None:
        prevalence = {"normal": 0.0, "low": 0.0, "medium": 0.0, "high": 1.0, "critical": 0.0}
        result = cost_model.scenario_for_prevalence("keyword", Path("evals/results/good_keyword"), META, [row("high", "escalate_to_moderator", True)], "test", prevalence)
        self.assertEqual(float(result["expected_fallback_cost_per_1000_comments"]), 0.0)
        self.assertEqual(float(result["necessary_review_load_per_1000"]), 1000.0)

    def test_invalid_run_is_rejected(self) -> None:
        invalid = dict(META)
        invalid["valid_run"] = False
        with self.assertRaises(ValueError):
            cost_model.validate_run(invalid)


if __name__ == "__main__":
    unittest.main()
