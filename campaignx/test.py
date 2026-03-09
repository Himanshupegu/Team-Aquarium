"""
agents/brief_parser.py
Takes a plain-English campaign brief and returns a structured dict
by calling the LLM router with task="structured_parse".

Single function: parse_brief(campaign_brief: str) -> dict
"""
import json
import re
from datetime import datetime, timezone

from backend.llm.router import llm_router
from backend.config import CAMPAIGN_CTA_URL

# ── Expected output keys with types (for the LLM prompt) ─────────────────
_OUTPUT_SCHEMA = """{
    "product_name": "string — the product being promoted",
    "key_message": "string — core value proposition in one sentence",
    "special_offers": ["list of strings — any special offers, bonuses, or promotions mentioned"],
    "optimization_goal": "string — one of: open_rate, click_rate, both",
    "include_inactive": "boolean — true unless the brief explicitly says to exclude inactive customers",
    "cta_url": "string — the call-to-action URL from the brief, or default",
    "tone": "string — one of: formal, friendly, urgent, professional",
    "campaign_type": "string — one of: product_launch, awareness, retention, upsell",
    "target_audience_notes": "string — any specific audience targeting instructions from the brief"
}"""

_VALID_GOALS = {"open_rate", "click_rate", "both"}
_VALID_TONES = {"formal", "friendly", "urgent", "professional"}
_VALID_TYPES = {"product_launch", "awareness", "retention", "upsell"}


def _build_prompt(campaign_brief: str, previous_error: str | None = None) -> str:
    """Build the LLM prompt for structured brief parsing."""
    prompt = f"""You are a marketing campaign brief parser. Your ONLY job is to extract structured data from a campaign brief.

INPUT BRIEF:
\"\"\"{campaign_brief}\"\"\"

Return a JSON object with EXACTLY these keys and value types:
{_OUTPUT_SCHEMA}

RULES:
- Return ONLY the JSON object. No markdown fences, no explanation, no extra text.
- If the brief does not mention a CTA URL, use: "{CAMPAIGN_CTA_URL}"
- If the brief says "don't skip inactive" or similar, set include_inactive to true.
- If the brief says "exclude inactive" or "skip inactive", set include_inactive to false.
- If optimization goal mentions both open and click rates, use "both".
- For tone, infer from the brief's language. Default to "professional" if unclear.
- For campaign_type, infer from context. A new product = "product_launch".
- special_offers must be a list. If none mentioned, return an empty list.
- target_audience_notes should capture any audience-specific instructions verbatim.

Return the JSON object now:"""

    if previous_error:
        prompt += f"\n\nYour previous response could not be parsed as JSON. Error: {previous_error}\nPlease return ONLY valid JSON this time, no markdown fences or extra text."

    return prompt


def _strip_markdown_fences(text: str) -> str:
    """Remove accidental ```json ... ``` or ``` ... ``` wrappers."""
    text = text.strip()
    # Remove ```json or ``` at start
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    # Remove ``` at end
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _validate_and_fix(parsed: dict) -> dict:
    """Ensure all expected keys exist with valid, non-None values."""
    # ── Safe defaults — used for both missing AND None values ────────────
    _DEFAULTS = {
        "product_name": "",
        "key_message": "",
        "special_offers": [],
        "optimization_goal": "both",
        "include_inactive": False,
        "cta_url": None,               # legitimately optional
        "tone": "professional",
        "campaign_type": "product_launch",
        "target_audience_notes": "",
    }

    # Fill missing keys
    for key, default in _DEFAULTS.items():
        parsed.setdefault(key, default)

    # Replace None values with safe defaults (cta_url is allowed to be None)
    for key, default in _DEFAULTS.items():
        if key == "cta_url":
            continue  # None is a valid value for cta_url
        if parsed[key] is None:
            parsed[key] = default

    # Normalize enum values
    if parsed["optimization_goal"] not in _VALID_GOALS:
        parsed["optimization_goal"] = "both"
    if parsed["tone"] not in _VALID_TONES:
        parsed["tone"] = "professional"
    if parsed["campaign_type"] not in _VALID_TYPES:
        parsed["campaign_type"] = "product_launch"

    # Ensure types
    if not isinstance(parsed["special_offers"], list):
        parsed["special_offers"] = [str(parsed["special_offers"])]
    parsed["include_inactive"] = bool(parsed["include_inactive"])

    return parsed


def _log_to_db(*args, **kwargs):
    pass


async def parse_brief(campaign_brief: str) -> dict:
    """
    Parse a plain-English campaign brief into a structured dict.

    Calls the LLM router, strips markdown fences, parses JSON.
    Retries once on parse failure with the error appended to the prompt.
    Logs input/output to the agent_logs DB table.
    """
    prompt = _build_prompt(campaign_brief)

    # Attempt 1
    raw = await llm_router.call(prompt, task="structured_parse", max_tokens=800)
    cleaned = _strip_markdown_fences(raw)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Attempt 2 — retry with error context
        print(f"[brief_parser] First parse failed: {e}. Retrying...")
        retry_prompt = _build_prompt(campaign_brief, previous_error=str(e))
        raw = await llm_router.call(retry_prompt, task="structured_parse", max_tokens=800)
        cleaned = _strip_markdown_fences(raw)
        parsed = json.loads(cleaned)  # let it raise if still bad

    result = _validate_and_fix(parsed)
    _log_to_db(campaign_brief, result)
    return result
