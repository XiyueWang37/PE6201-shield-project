"""LLM-backed Shield severity classifier.

This module provides the same `classify_comment(comment, context="")` surface
as the keyword fallback, but routes the classification through a hosted chat
model. It reads credentials only from `SHIELD_API_KEY`, caches responses under
`evals/cache/`, and returns abstention metadata for evaluation scripts.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from policy import action_for_severity, log_decision
from shield_classifier import ShieldResult

CONFIG = {
    "BACKEND": os.getenv("SHIELD_LLM_BACKEND", "openai_compatible"),
    "MODEL": os.getenv("SHIELD_LLM_MODEL", "openai/gpt-4o-mini"),
    "BASE_URL": os.getenv("SHIELD_LLM_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"),
    "CACHE_PATH": "evals/cache/llm_responses.jsonl",
    "TEMPERATURE": 0,
    "MAX_TOKENS": 220,
    "TIMEOUT_SECONDS": 45,
    "MAX_RETRIES": 2,
}

VALID_SEVERITIES = {"normal", "low", "medium", "high", "critical"}


@dataclass
class LLMRawResponse:
    """Raw response payload plus provider usage metadata."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0


def build_prompt(comment: str, context: str = "") -> list[dict[str, str]]:
    """Build a deterministic JSON-only harassment classification prompt."""
    system = (
        "You classify social media harassment severity. Use exactly one label:\n"
        "- normal: ordinary disagreement, criticism, or neutral text.\n"
        "- low: rude or mildly hostile, but not targeted harassment.\n"
        "- medium: direct insult, targeted hostility, or repeated unwanted contact.\n"
        "- high: credible threat, stalking cue, intimidation, or severe harassment.\n"
        "- critical: explicit violence, doxxing, identity-targeted severe abuse, or urgent safety risk.\n"
        "Return only JSON with keys severity, rationale, confidence, abstain. "
        "confidence must be low, medium, or high. abstain is true when the evidence is insufficient."
    )
    user = {
        "context": context or "",
        "comment": comment,
        "required_json_schema": {
            "severity": "normal|low|medium|high|critical",
            "rationale": "short explanation",
            "confidence": "low|medium|high",
            "abstain": "boolean",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def estimate_tokens_for_messages(messages: list[dict[str, str]]) -> int:
    """Estimate tokens before an API call using a conservative character ratio."""
    chars = sum(len(message["content"]) for message in messages)
    return max(1, (chars + 3) // 4)


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Return an assumed low-cost estimate for pre-call safety printing.

    ASSUMED prices, pending user verification against the provider price page:
    USD 0.15 / 1M input tokens and USD 0.60 / 1M output tokens.
    """
    return (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)


def _cache_key(model: str, messages: list[dict[str, str]]) -> str:
    raw = json.dumps({"model": model, "messages": messages}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    cache: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            cache[record["key"]] = record
    return cache


def _append_cache(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def call_provider(messages: list[dict[str, str]]) -> LLMRawResponse:
    """Call an OpenAI-compatible chat completion endpoint."""
    api_key = os.getenv("SHIELD_API_KEY")
    if not api_key:
        raise RuntimeError("SHIELD_API_KEY is not set")

    payload = {
        "model": CONFIG["MODEL"],
        "messages": messages,
        "temperature": CONFIG["TEMPERATURE"],
        "max_tokens": CONFIG["MAX_TOKENS"],
    }
    request = urllib.request.Request(
        str(CONFIG["BASE_URL"]),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=int(CONFIG["TIMEOUT_SECONDS"])) as response:
        data = json.loads(response.read().decode("utf-8"))

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    return LLMRawResponse(
        content=content,
        input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
    )


def _parse_json_response(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    data = json.loads(cleaned)
    severity = str(data.get("severity", "")).strip().lower()
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity: {severity}")
    confidence = str(data.get("confidence", "low")).strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    return {
        "severity": severity,
        "rationale": str(data.get("rationale", "")).strip() or "No rationale returned.",
        "confidence": confidence,
        "abstain": bool(data.get("abstain", False)),
    }


def _abstain_result(comment: str, context: str, reason: str, input_tokens: int = 0) -> ShieldResult:
    severity = "abstain"
    action = action_for_severity(severity)
    log_decision(comment, context, severity, action, backend="llm")
    return ShieldResult(
        severity=severity,
        rationale=reason,
        confidence="low",
        policy_action=action,
        input_tokens=input_tokens,
        output_tokens=0,
        abstain=True,
    )


def classify_comment(comment: str, context: str = "") -> ShieldResult:
    """Classify a comment through the configured LLM backend."""
    messages = build_prompt(comment, context)
    estimated_input = estimate_tokens_for_messages(messages)
    estimated_cost = estimate_cost_usd(estimated_input, int(CONFIG["MAX_TOKENS"]))
    print(
        "LLM preflight: "
        f"estimated_input_tokens={estimated_input}, "
        f"max_output_tokens={CONFIG['MAX_TOKENS']}, "
        f"estimated_cost_usd={estimated_cost:.6f}"
    )
    if estimated_cost > 2:
        return _abstain_result(comment, context, "Estimated API cost exceeds USD 2.", estimated_input)

    cache_path = Path(str(CONFIG["CACHE_PATH"]))
    key = _cache_key(str(CONFIG["MODEL"]), messages)
    cache = _load_cache(cache_path)
    if key in cache:
        cached = cache[key]
        raw = LLMRawResponse(
            content=str(cached["content"]),
            input_tokens=int(cached.get("input_tokens", 0)),
            output_tokens=int(cached.get("output_tokens", 0)),
        )
    else:
        for attempt in range(int(CONFIG["MAX_RETRIES"]) + 1):
            try:
                raw = call_provider(messages)
                _append_cache(
                    cache_path,
                    {
                        "key": key,
                        "model": CONFIG["MODEL"],
                        "content": raw.content,
                        "input_tokens": raw.input_tokens,
                        "output_tokens": raw.output_tokens,
                    },
                )
                break
            except (RuntimeError, urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
                if attempt >= int(CONFIG["MAX_RETRIES"]):
                    return _abstain_result(comment, context, f"LLM call failed: {exc}", estimated_input)
                time.sleep(1)

    try:
        parsed = _parse_json_response(raw.content)
    except (ValueError, json.JSONDecodeError) as exc:
        return _abstain_result(comment, context, f"LLM response parsing failed: {exc}", raw.input_tokens)

    severity = "abstain" if parsed["abstain"] else parsed["severity"]
    action = action_for_severity(severity)
    log_decision(comment, context, severity, action, backend="llm")
    return ShieldResult(
        severity=severity,
        rationale=parsed["rationale"],
        confidence=parsed["confidence"],
        policy_action=action,
        input_tokens=raw.input_tokens,
        output_tokens=raw.output_tokens,
        abstain=bool(parsed["abstain"]),
    )
