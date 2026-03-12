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

    if cta_url and cta_url not in body:
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

    # Ensure CTA URL in body — only if cta_url is provided
    if cta_url and cta_url not in body:
        fallback_button = f'\n<br><br><a href="{cta_url}" style="display: inline-block; padding: 10px 20px; font-weight: bold; text-decoration: none; color: #ffffff; background-color: #007bff; border-radius: 5px;">Claim Your Offer</a>'
        max_body_before_url = MAX_BODY_CHARS - len(fallback_button)
        body = body[:max_body_before_url] + fallback_button

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
    is_retargeting: bool = False,
) -> str:
    """Build the LLM prompt for email content generation."""

    # Variant-specific instructions
    if getattr(segment, "size", 0) > 100:
        if variant_label.upper() == "A":
            variant_instruction = (
                "VARIANT A (Rational/Benefit-driven): Lead with specific numbers — e.g. '1% higher returns than competitors', "
                "'additional 0.25% for female senior citizens' if applicable. Use bullet points listing concrete financial benefits. "
                "Tone should match the segment persona perfectly. End with the HTML anchor CTA."
            )
        else:
            variant_instruction = (
                "VARIANT B (Urgency/FOMO-driven): Open with a fear-of-missing-out hook specific to the persona "
                "(e.g. wealth-building urgency for high earners, retirement security urgency for seniors). "
                "NO bullet points — use short punchy paragraphs only. Create strong time pressure with phrases "
                "like 'Start growing your savings today'. End with the HTML anchor CTA."
            )
    else:
        if variant_label.upper() == "A":
            variant_instruction = (
                "VARIANT A (Rational): use bullet points to list 2-3 concrete benefits, then CTA"
            )
        else:
            variant_instruction = (
                "VARIANT B (Emotional): use 2 short punchy paragraphs with emotional hook, then CTA"
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
        if is_retargeting:
            perf_context += (
                "\nThis segment was previously contacted but engagement was low. Generate "
                "a completely different subject line and email opening hook from the previous attempt. "
                "Try a different angle, tone, and value proposition to convert customers who did not engage before.\n"
            )

    prompt = f"""You are an expert email copywriter for SuperBFSI, an Indian BFSI company.

PRODUCT: {parsed_brief.get("product_name", "XDeposit")}
KEY MESSAGE: {parsed_brief.get("key_message", "")}
SPECIAL OFFERS:
{offers_text}
CTA URL: {parsed_brief.get("cta_url", "") or "None provided"}

TARGET SEGMENT: {segment.label}
SEGMENT USP: {segment.key_usp}
PERSONA: {segment.persona_hint}
RECOMMENDED TONE: {segment.recommended_tone}

{variant_instruction}
{perf_context}
STRICT RULES:
1. subject: English text ONLY, NO URLs, NO emojis, max {MAX_SUBJECT_CHARS} characters. Must be under 50 characters, curiosity-driving or benefit-stating, no generic phrases like "Earn Rewards with NeoSavings".
2. body: English text, HTML tags <b>, <i>, <u>, <a>, <br> allowed. Keep the email body short and scannable — maximum 150 words AND max {MAX_BODY_CHARS} characters, using short paragraphs of 1-2 sentences each. IMPORTANT: Use <br><br> tags for paragraph breaks and <br> for line breaks. Do NOT use \n or newline escape sequences — only HTML <br> tags!
3. Open with a strong hook line directly relevant to the segment persona (e.g. for families_with_kids, lead with the child's financial future angle).
4. State the core benefit (e.g., ₹300 per referral) within the first 2 lines — don't bury it.
5. If CTA URL is provided, include it exactly once. You MUST format it strictly as a beautiful HTML button using inline CSS, with <br><br> before and after the button. The button text inside the tag must be concise (2-5 words), use strong action verbs (avoid 'Click Here'), and use personalized pronouns (e.g. 'Claim My Reward'). Example: <br><br><a href="THE_CTA_URL" style="display: inline-block; padding: 10px 20px; font-weight: bold; text-decoration: none; color: #ffffff; background-color: #007bff; border-radius: 5px;">Action Phrase Here</a><br><br>. Do NOT paste the raw URL as plain text!
6. For bullet points, use the HTML bullet character • with <br> before each bullet. Do NOT use markdown-style bullets like * or -.
7. Do NOT use any other URLs in subject or body.
8. Use 2-3 emojis maximum as visual anchors at the start of key lines, not mid-sentence.
9. Make the email feel personal and relevant to this specific segment.

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

def _clean_json_string(text: str) -> str:
    """Aggressive cleaning for JSON parsing: strip markdown, replace quotes, remove control chars."""
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    
    # Replace curly quotes and apostrophes
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    
    # Regex to remove control characters (except newline and tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    return text.strip()


def _log_to_db(campaign_id: str, segment_label: str, variant_label: str, iteration: int, result: dict) -> None:
    """Log the generation result to agent_logs."""
    import json as _json
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog

    msg = _json.dumps({
        "iteration": iteration,
        "segment": segment_label,
        "variant": variant_label,
        "subject": result["subject"],
        "body": result["body"],
        "strategy_notes": result["strategy_notes"],
        "reasoning": f"Generated variant {variant_label} for segment '{segment_label}' "
                     f"(iteration {iteration})",
    })

    db = SessionLocal()
    try:
        log = AgentLog(
            created_at=datetime.now(timezone.utc),
            campaign_id=campaign_id,
            agent_name="content_gen",
            message=msg,
        )
        db.add(log)
        db.commit()
        print(f"[content_gen] Logged to agent_logs table")
    finally:
        db.close()


async def generate_content(
    campaign_id: str,
    parsed_brief: dict,
    segment: Segment,
    variant_label: str,
    iteration: int,
    prev_performance: list[dict] = None,
    is_retargeting: bool = False,
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
    cta_url = parsed_brief.get("cta_url", "") or ""

    # ── Attempt 1 ────────────────────────────────────────────────────────
    prompt = _build_prompt(
        parsed_brief, segment, variant_label, iteration, prev_performance, is_retargeting=is_retargeting
    )
    raw = await llm_router.call(prompt, task="content_gen", max_tokens=1500)
    cleaned = _clean_json_string(raw)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[content_gen] JSON parse failed: {e}. Retrying...")
        retry_prompt = prompt + (
            f"\n\nJSON parse error: {e}\n"
            "Your previous response contained invalid JSON. Return ONLY valid JSON with no special characters, "
            "no curly quotes, no apostrophes in values — use straight quotes only. "
            "Escape any quotes inside string values with backslash."
        )
        raw = await llm_router.call(retry_prompt, task="content_gen", max_tokens=1500)
        cleaned = _clean_json_string(raw)
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
            validation_errors=errors, is_retargeting=is_retargeting,
        )
        raw = await llm_router.call(retry_prompt, task="content_gen", max_tokens=1500)
        cleaned = _clean_json_string(raw)

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

    _log_to_db(campaign_id, segment.label, variant_label, iteration, final)
    print(f"[content_gen] Generated variant {variant_label} for '{segment.label}' "
          f"(subject: {len(subject)} chars, body: {len(body)} chars)")
    return final
