"""Deterministic policy table for Shield.

The classifier estimates harassment severity. This module owns the product
decision so that actions remain transparent, auditable, and easy to tune.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

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


def log_decision(
    comment: str,
    context: str,
    severity: str,
    action: str,
    backend: str,
    log_path: str | Path = "evals/logs/policy_decisions.jsonl",
) -> None:
    """Append a policy decision record without storing raw comment text."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_hash": hashlib.sha256(f"{context}\n{comment}".encode("utf-8")).hexdigest(),
        "severity": severity,
        "action": action,
        "backend": backend,
    }
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
