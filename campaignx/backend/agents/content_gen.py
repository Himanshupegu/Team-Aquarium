"""
agents/content_gen.py
Generates personalised email subject + body for a single segment using the LLM.

Single public function:
    generate_content(parsed_brief, segment, variant_label, iteration, prev_performance) -> dict

Returns: {"subject": str, "body": str, "strategy_notes": str}
"""
import json
import re
from datetime import datetime, timezone

from backend.llm.router import llm_router
from backend.config import CAMPAIGN_CTA_URL, MAX_SUBJECT_CHARS, MAX_BODY_CHARS
from backend.agents.profiler import Segment


# ═══════════════════════════════════════════════════════════════════════════
# CONTENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def validate_content(subject: str, body: str, cta_url: str) -> list[str]:
    """
    Validate subject and body against hackathon content rules.
    Returns a list of error strings (empty = all good).
    """
    errors = []

    if len(subject) > MAX_SUBJECT_CHARS:
        errors.append(f"Subject is {len(subject)} chars (max {MAX_SUBJECT_CHARS})")

    if re.search(r"https?://", subject):
        errors.append("Subject contains a URL (not allowed)")

    if cta_url not in body:
        errors.append(f"Body is missing the CTA URL: {cta_url}")

    if len(body) > MAX_BODY_CHARS:
        errors.append(f"Body is {len(body)} chars (max {MAX_BODY_CHARS})")

    return errors


def _fix_content_programmatically(subject: str, body: str, cta_url: str) -> tuple[str, str]:
    """
    Last-resort fixes when LLM can't get it right after retry.
    Truncate subject, strip URLs from subject, append CTA to body.
    """
    # Remove URLs from subject
    subject = re.sub(r"https?://\S+", "", subject).strip()

    # Truncate subject
    if len(subject) > MAX_SUBJECT_CHARS:
        subject = subject[: MAX_SUBJECT_CHARS - 3].rstrip() + "..."

    # Ensure CTA URL in body — trim body first to make room, then append
    if cta_url not in body:
        max_body_before_url = MAX_BODY_CHARS - 1 - len(cta_url)  # 1 for \n
        body = body[:max_body_before_url] + "\n" + cta_url

    # Truncate body if still over limit (e.g. CTA was already present but body too long)
    if len(body) > MAX_BODY_CHARS:
        body = body[: MAX_BODY_CHARS - 3].rstrip() + "..."

    return subject, body


# ═══════════════════════════════════════════════════════════════════════════
# PROMPT BUILDING
# ═══════════════════════════════════════════════════════════════════════════

def _build_prompt(
    parsed_brief: dict,
    segment: Segment,
    variant_label: str,
    iteration: int,
    prev_performance: list[dict],
    validation_errors: list[str] | None = None,
) -> str:
    """Build the LLM prompt for email content generation."""

    # Variant-specific instructions
    if variant_label.upper() == "A":
        variant_instruction = (
            "VARIANT A: Lead with data and rational benefit. Use a more formal, "
            "authoritative tone. Emphasize numbers, facts, and logical reasons to act."
        )
    else:
        variant_instruction = (
            "VARIANT B: Lead with emotion and aspiration. Use a more conversational, "
            "warm tone. Emphasize dreams, lifestyle improvement, and personal stories."
        )

    # Special offers
    special_offers = parsed_brief.get("special_offers", [])
    offers_text = "\n".join(f"  - {offer}" for offer in special_offers) if special_offers else "  None"

    # Previous performance context (iteration > 1)
    perf_context = ""
    if iteration > 1 and prev_performance:
        perf_context = "\nPREVIOUS CAMPAIGN PERFORMANCE:\n"
        for p in prev_performance:
            perf_context += (
                f"  - Segment: {p.get('segment', '?')}, Variant: {p.get('variant', '?')}, "
                f"Open rate: {p.get('open_rate', '?')}, Click rate: {p.get('click_rate', '?')}\n"
            )
        perf_context += (
            "\nThis is iteration {iteration}. The previous results are above. "
            "Try a DIFFERENT approach this time: vary subject length, emoji density, "
            "CTA placement, or body length compared to what was tried before.\n"
        )

    prompt = f"""You are an expert email copywriter for SuperBFSI, an Indian BFSI company.

PRODUCT: {parsed_brief.get("product_name", "XDeposit")}
KEY MESSAGE: {parsed_brief.get("key_message", "")}
SPECIAL OFFERS:
{offers_text}
CTA URL (must include exactly once in body): {parsed_brief.get("cta_url", CAMPAIGN_CTA_URL)}

TARGET SEGMENT: {segment.label}
SEGMENT USP: {segment.key_usp}
PERSONA: {segment.persona_hint}
RECOMMENDED TONE: {segment.recommended_tone}

{variant_instruction}
{perf_context}
STRICT RULES:
1. subject: English text ONLY, NO URLs, NO emojis, max {MAX_SUBJECT_CHARS} characters
2. body: English text, emojis allowed ✅, HTML tags <b>, <i>, <u> allowed
3. body MUST include this CTA URL exactly once: {parsed_brief.get("cta_url", CAMPAIGN_CTA_URL)}
4. body max {MAX_BODY_CHARS} characters
5. Do NOT use any other URLs in subject or body
6. Make the email feel personal and relevant to this specific segment

Return ONLY a JSON object with these keys:
  "subject": the email subject line
  "body": the full email body
  "strategy_notes": one sentence explaining your content strategy for this variant

No markdown fences, no explanation, ONLY the JSON object."""

    if validation_errors:
        prompt += (
            "\n\nYour previous response had these validation errors:\n"
            + "\n".join(f"  - {e}" for e in validation_errors)
            + "\n\nFix ALL errors this time. Return ONLY valid JSON."
        )

    return prompt


# ═══════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def _strip_markdown_fences(text: str) -> str:
    """Remove accidental ```json ... ``` wrappers."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _log_to_db(segment_label: str, variant_label: str, iteration: int, result: dict) -> None:
    """Log the generation result to agent_logs."""
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog

    db = SessionLocal()
    try:
        log = AgentLog(
            timestamp=datetime.now(timezone.utc),
            agent_name="content_gen",
            iteration=iteration,
            input_data={
                "segment": segment_label,
                "variant": variant_label,
            },
            output_data={
                "subject": result["subject"],
                "body_preview": result["body"][:200],
                "strategy_notes": result["strategy_notes"],
            },
            reasoning=f"Generated variant {variant_label} for segment '{segment_label}' "
                      f"(iteration {iteration})",
        )
        db.add(log)
        db.commit()
        print(f"[content_gen] Logged to agent_logs table")
    finally:
        db.close()


async def generate_content(
    parsed_brief: dict,
    segment: Segment,
    variant_label: str,
    iteration: int,
    prev_performance: list[dict],
) -> dict:
    """
    Generate a personalised email subject + body for one segment.

    Args:
        parsed_brief: Output from parse_brief()
        segment: A Segment object from the profiler
        variant_label: "A" or "B"
        iteration: Campaign iteration number (1-based)
        prev_performance: List of dicts with previous campaign metrics (empty on iteration 1)

    Returns:
        {"subject": str, "body": str, "strategy_notes": str}
    """
    cta_url = parsed_brief.get("cta_url", CAMPAIGN_CTA_URL)

    # ── Attempt 1 ────────────────────────────────────────────────────────
    prompt = _build_prompt(parsed_brief, segment, variant_label, iteration, prev_performance)
    raw = await llm_router.call(prompt, task="content_gen", max_tokens=1500)
    cleaned = _strip_markdown_fences(raw)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[content_gen] JSON parse failed: {e}. Retrying...")
        retry_prompt = prompt + f"\n\nJSON parse error: {e}\nReturn ONLY valid JSON."
        raw = await llm_router.call(retry_prompt, task="content_gen", max_tokens=1500)
        cleaned = _strip_markdown_fences(raw)
        result = json.loads(cleaned)

    subject = result.get("subject", "")
    body = result.get("body", "")
    strategy_notes = result.get("strategy_notes", "")

    # ── Validate attempt 1 ───────────────────────────────────────────────
    errors = validate_content(subject, body, cta_url)

    if errors:
        print(f"[content_gen] Validation errors (attempt 1): {errors}")

        # ── Attempt 2 — retry with errors ────────────────────────────────
        retry_prompt = _build_prompt(
            parsed_brief, segment, variant_label, iteration, prev_performance,
            validation_errors=errors,
        )
        raw = await llm_router.call(retry_prompt, task="content_gen", max_tokens=1500)
        cleaned = _strip_markdown_fences(raw)

        try:
            result = json.loads(cleaned)
            subject = result.get("subject", subject)
            body = result.get("body", body)
            strategy_notes = result.get("strategy_notes", strategy_notes)
        except json.JSONDecodeError:
            print("[content_gen] Retry also failed JSON parse — keeping attempt 1 output")

        # ── Validate attempt 2 ───────────────────────────────────────────
        errors = validate_content(subject, body, cta_url)

        if errors:
            # ── Programmatic fix — last resort ───────────────────────────
            print(f"[content_gen] Validation still failing: {errors}. Fixing programmatically.")
            subject, body = _fix_content_programmatically(subject, body, cta_url)

    final = {
        "subject": subject,
        "body": body,
        "strategy_notes": strategy_notes,
    }

    _log_to_db(segment.label, variant_label, iteration, final)
    print(f"[content_gen] Generated variant {variant_label} for '{segment.label}' "
          f"(subject: {len(subject)} chars, body: {len(body)} chars)")
    return final
