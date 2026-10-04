"""LLM-backed Shield severity classifier.

The module keeps the same `classify_comment(comment, context="")` surface as the
local keyword fallback. Cached responses are checked before credentials are
required, so a committed cache can be replayed by a marker without an API key.
New uncached calls require `SHIELD_API_KEY` and record provider usage tokens.
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

from policy import action_for_severity
from shield_classifier import ShieldResult

ROOT = Path(__file__).resolve().parents[1]
PROMPT_VERSION = os.getenv("SHIELD_PROMPT_VERSION", "prompt_v2")
CONFIG = {
    "BACKEND": os.getenv("SHIELD_LLM_BACKEND", "openai_compatible"),
    "MODEL": os.getenv("SHIELD_LLM_MODEL", "openai/gpt-4o-mini"),
    "MODEL_TIER": os.getenv("SHIELD_MODEL_TIER", "cheap_assumed"),
    "BASE_URL": os.getenv("SHIELD_LLM_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"),
    "CACHE_PATH": os.getenv("SHIELD_LLM_CACHE_PATH", str(ROOT / "evals" / "cache" / "llm_responses.jsonl")),
    "TEMPERATURE": 0,
    "MAX_TOKENS": 220,
    "TIMEOUT_SECONDS": 45,
    "MAX_RETRIES": 2,
    "ASSUMED_INPUT_PER_MILLION_USD": 0.15,
    "ASSUMED_OUTPUT_PER_MILLION_USD": 0.60,
}

VALID_SEVERITIES = {"normal", "low", "medium", "high", "critical"}


@dataclass
class LLMRawResponse:
    """Raw response payload plus provider usage metadata."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    from_cache: bool = False


def build_prompt(comment: str, context: str = "") -> list[dict[str, str]]:
    """Build a deterministic JSON-only harassment classification prompt."""
    calibration = ""
    if PROMPT_VERSION == "prompt_v2":
        calibration = (
            "Calibration: targeted direct insults such as idiot, stupid, shut up, or worthlessness are at least medium; "
            "location, schedule, route, workplace, watching, waiting, or regret cues directed at a person are at least high; "
            "private address, private messages, doxxing, or explicit offline danger are critical when severe. "
            "Do not escalate ordinary evidence-based criticism of work, ideas, designs, or arguments.\n"
        )
    system = (
        f"Prompt version: {PROMPT_VERSION}.\n"
        "You classify social media harassment severity. Use exactly one label:\n"
        "- normal: ordinary disagreement, criticism, or neutral text.\n"
        "- low: rude or mildly hostile, but not targeted harassment.\n"
        "- medium: direct insult, targeted hostility, or repeated unwanted contact.\n"
        "- high: credible threat, stalking cue, intimidation, or severe harassment.\n"
        "- critical: explicit violence, doxxing, identity-targeted severe abuse, or urgent safety risk.\n"
        + calibration +
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
    chars = sum(len(message["content"]) for message in messages)
    return max(1, (chars + 3) // 4)


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * float(CONFIG["ASSUMED_INPUT_PER_MILLION_USD"]) / 1_000_000
        + output_tokens * float(CONFIG["ASSUMED_OUTPUT_PER_MILLION_USD"]) / 1_000_000
    )


def _cache_key(model: str, messages: list[dict[str, str]]) -> str:
    raw = json.dumps(
        {"model": model, "prompt_version": PROMPT_VERSION, "messages": messages},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_path() -> Path:
    return Path(str(CONFIG["CACHE_PATH"]))


def _load_cache(path: Path | None = None) -> dict[str, dict[str, Any]]:
    target = path or cache_path()
    if not target.exists():
        return {}
    cache: dict[str, dict[str, Any]] = {}
    with target.open("r", encoding="utf-8") as handle:
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


def request_key(comment: str, context: str = "") -> str:
    return _cache_key(str(CONFIG["MODEL"]), build_prompt(comment, context))


def has_cached_response(comment: str, context: str = "") -> bool:
    return request_key(comment, context) in _load_cache()


def preflight_for_rows(rows: list[dict[str, str]], comment_field: str = "comment", context_field: str = "context") -> dict[str, object]:
    total_input = 0
    total_output = 0
    cache = _load_cache()
    missing_cache = 0
    for row in rows:
        messages = build_prompt(row[comment_field], row.get(context_field, ""))
        total_input += estimate_tokens_for_messages(messages)
        total_output += int(CONFIG["MAX_TOKENS"])
        if _cache_key(str(CONFIG["MODEL"]), messages) not in cache:
            missing_cache += 1
    return {
        "model": CONFIG["MODEL"],
        "model_tier": CONFIG["MODEL_TIER"],
        "base_url": CONFIG["BASE_URL"],
        "prompt_version": PROMPT_VERSION,
        "call_count": len(rows),
        "estimated_input_tokens": total_input,
        "estimated_output_tokens": total_output,
        "estimated_cost_usd": estimate_cost_usd(total_input, total_output),
        "missing_cache_count": missing_cache,
        "has_api_key": bool(os.getenv("SHIELD_API_KEY")),
    }


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


def _abstain_result(reason: str, input_tokens: int = 0, error_type: str = "model_abstain") -> ShieldResult:
    severity = "abstain"
    return ShieldResult(
        severity=severity,
        rationale=reason,
        confidence="low",
        policy_action=action_for_severity(severity),
        input_tokens=input_tokens,
        output_tokens=0,
        abstain=True,
        error_type=error_type,
    )


def classify_comment(comment: str, context: str = "") -> ShieldResult:
    """Classify a comment through the configured LLM backend."""
    messages = build_prompt(comment, context)
    estimated_input = estimate_tokens_for_messages(messages)
    key = _cache_key(str(CONFIG["MODEL"]), messages)
    cache = _load_cache()
    if key in cache:
        cached = cache[key]
        raw = LLMRawResponse(
            content=str(cached["content"]),
            input_tokens=int(cached.get("input_tokens", 0)),
            output_tokens=int(cached.get("output_tokens", 0)),
            from_cache=True,
        )
    else:
        estimated_cost = estimate_cost_usd(estimated_input, int(CONFIG["MAX_TOKENS"]))
        if estimated_cost > 2:
            return _abstain_result("Estimated API cost exceeds USD 2.", estimated_input, "api_error")
        for attempt in range(int(CONFIG["MAX_RETRIES"]) + 1):
            try:
                raw = call_provider(messages)
                _append_cache(
                    cache_path(),
                    {
                        "key": key,
                        "model": CONFIG["MODEL"],
                        "prompt_version": PROMPT_VERSION,
                        "content": raw.content,
                        "input_tokens": raw.input_tokens,
                        "output_tokens": raw.output_tokens,
                    },
                )
                break
            except (RuntimeError, urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
                if attempt >= int(CONFIG["MAX_RETRIES"]):
                    return _abstain_result(f"LLM call failed: {exc}", estimated_input, "api_error")
                time.sleep(1)

    try:
        parsed = _parse_json_response(raw.content)
    except (ValueError, json.JSONDecodeError) as exc:
        return _abstain_result(f"LLM response parsing failed: {exc}", raw.input_tokens, "api_error")

    if parsed["abstain"]:
        return _abstain_result(parsed["rationale"], raw.input_tokens, "model_abstain")
    severity = parsed["severity"]
    return ShieldResult(
        severity=severity,
        rationale=parsed["rationale"],
        confidence=parsed["confidence"],
        policy_action=action_for_severity(severity),
        input_tokens=raw.input_tokens,
        output_tokens=raw.output_tokens,
        abstain=False,
    )
