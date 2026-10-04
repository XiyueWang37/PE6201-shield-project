"""Command line demo for Shield."""

from policy import log_decision
from shield_classifier import classify_comment


EXAMPLES = [
    {
        "name": "Normal criticism",
        "context": "",
        "comment": "I disagree with your conclusion because the evidence is weak.",
    },
    {
        "name": "Direct insult",
        "context": "",
        "comment": "You are such an idiot and should shut up.",
    },
    {
        "name": "Context-sensitive escalation",
        "context": "User A: Stop messaging me. User B: I know where you usually go after class.",
        "comment": "I will see you again.",
    },
]


def main() -> None:
    for example in EXAMPLES:
        result = classify_comment(example["comment"], example["context"])
        log_decision(example["comment"], example["context"], result.severity, result.policy_action, backend="demo_keyword")
        print("=" * 72)
        print(example["name"])
        print(f"Context: {example['context'] or '[none]'}")
        print(f"Comment: {example['comment']}")
        print(f"Severity: {result.severity}")
        print(f"Action: {result.policy_action}")
        print(f"Confidence: {result.confidence}")
        print(f"Rationale: {result.rationale}")


if __name__ == "__main__":
    main()
