"""Deterministic policy table for Shield.

The classifier estimates harassment severity. This module owns the product
decision so that actions remain transparent, auditable, and easy to tune.
"""

POLICY_TABLE = {
    "normal": "allow",
    "low": "allow",
    "medium": "prompt_reconsider",
    "high": "escalate_to_moderator",
    "critical": "escalate_to_moderator",
}


def action_for_severity(severity: str) -> str:
    """Return the moderation action for a severity label."""
    normalized = severity.strip().lower()
    if normalized not in POLICY_TABLE:
        return "escalate_to_moderator"
    return POLICY_TABLE[normalized]
