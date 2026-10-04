"""Shield harassment severity classifier.

This file contains a local deterministic fallback so the project can be run
without an API key during marking. In the final build, this interface can be
connected to a hosted foundation model while keeping the policy layer stable.
"""

from dataclasses import dataclass

from policy import action_for_severity


@dataclass
class ShieldResult:
    severity: str
    rationale: str
    confidence: str
    policy_action: str
    input_tokens: int = 0
    output_tokens: int = 0
    abstain: bool = False
    error_type: str = ""


HIGH_RISK_TERMS = {
    "kill",
    "die",
    "threat",
    "hurt",
    "attack",
    "destroy you",
}

MEDIUM_RISK_TERMS = {
    "stupid",
    "idiot",
    "shut up",
    "worthless",
    "loser",
}


def classify_comment(comment: str, context: str = "") -> ShieldResult:
    """Classify a comment with optional context.

    This fallback is deliberately simple. It exists to make the repository
    runnable and to demonstrate the data flow. The report should distinguish
    this fallback from any measured LLM run.
    """
    combined = f"{context}\n{comment}".lower()

    if any(term in combined for term in HIGH_RISK_TERMS):
        severity = "high"
        rationale = "The text contains language associated with threats or severe harassment."
        confidence = "medium"
    elif any(term in combined for term in MEDIUM_RISK_TERMS):
        severity = "medium"
        rationale = "The text contains direct insulting or hostile language."
        confidence = "medium"
    elif "again" in comment.lower() and context.strip():
        severity = "medium"
        rationale = "The final comment is ambiguous alone but may continue a hostile pattern in context."
        confidence = "low"
    else:
        severity = "normal"
        rationale = "No clear harassment signal was detected in this prototype pass."
        confidence = "low"

    return ShieldResult(
        severity=severity,
        rationale=rationale,
        confidence=confidence,
        policy_action=action_for_severity(severity),
    )
