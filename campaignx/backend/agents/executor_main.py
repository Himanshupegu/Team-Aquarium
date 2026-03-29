import json
from backend.agents.tool_definitions import CAMPAIGNX_TOOLS, TOOL_SELECTION_PROMPT

from datetime import datetime, timedelta, timezone

from backend.tools.api_tools import call_tool_by_name

IST = timezone(timedelta(hours=5, minutes=30))


def _discover_tool_via_llm(llm, task: str, log_callback=None) -> dict:
    """Use LLM to dynamically discover and select the appropriate API tool."""
    tool_definitions_str = json.dumps(CAMPAIGNX_TOOLS, indent=2)
    prompt = TOOL_SELECTION_PROMPT.format(
        tool_definitions=tool_definitions_str,
        task=task
    )
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, 'content') else str(response)
    
    # Clean and parse JSON response
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    
    result = json.loads(content)
    
    if log_callback:
        log_callback(
            f"Dynamically discovered and selected tool: '{result['tool_name']}' "
            f"based on API documentation. Reasoning: {result['reasoning']}"
        )
    
    return result


# ═══════════════════════════════════════════════════════════════════════════
# HELPER 1 — build_send_time
# ═══════════════════════════════════════════════════════════════════════════

def build_send_time(hour_ist: int, is_retargeting: bool = False) -> str:
    """
    Return send_time in DD:MM:YY HH:MM:SS format (2-digit year — critical).
    Schedules for hour_ist today in IST. If that hour has already passed, uses tomorrow.
    """
    if is_retargeting:
        hour_ist = 18 if hour_ist <= 12 else 9
        
    now = datetime.now(IST)
    send = now.replace(hour=hour_ist, minute=0, second=0, microsecond=0)
    if send <= now:
        send += timedelta(days=1)
    return send.strftime("%d:%m:%y %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════
# HELPER 2 — sanitize_customer_ids
# ═══════════════════════════════════════════════════════════════════════════

def sanitize_customer_ids(customer_ids: list[str], cohort_ids: set[str]) -> list[str]:
    """
    Remove IDs not in the cohort and deduplicate while preserving order.
    Logs a warning if any IDs were removed.
    """
    # Deduplicate preserving order
    deduped = list(dict.fromkeys(customer_ids))
    dup_count = len(customer_ids) - len(deduped)
    if dup_count > 0:
        print(f"[executor] Removed {dup_count} duplicate customer IDs")

    # Filter to valid cohort IDs
    valid = [cid for cid in deduped if cid in cohort_ids]
    removed_count = len(deduped) - len(valid)
    if removed_count > 0:
        print(f"[executor] WARNING: Removed {removed_count} customer IDs not found in cohort")

    return valid


# ═══════════════════════════════════════════════════════════════════════════
# HELPER 3 — save_campaign_to_db
# ═══════════════════════════════════════════════════════════════════════════

def save_campaign_to_db(
    campaign_id: str,
    iteration: int,
    segment_labels: list[str],
    subject: str,
    body: str,
    customer_ids: list[str],
    send_time: str,
    strategy_notes: str,
) -> None:
    """Save one campaign row to the campaigns table. Opens its own DB session."""
    from backend.db.session import SessionLocal
    from backend.db.models import Campaign

    db = SessionLocal()
    try:
        # Check if campaign already exists (e.g. from a previous iteration)
        existing = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if existing:
            # Update existing campaign with combined info
            existing.iteration = iteration
            existing.customer_ids = list(set((existing.customer_ids or []) + customer_ids))
            db.commit()
            print(f"[executor] Updated existing campaign {campaign_id} in DB")
        else:
            campaign = Campaign(
                campaign_id=campaign_id,
                iteration=iteration,
                variant_label="all",
                segment_label=", ".join(segment_labels),
                subject=subject,
                body=body,
                customer_ids=customer_ids,
                send_time=send_time,
                strategy_notes=strategy_notes,
            )
            db.add(campaign)
            db.commit()
            print(f"[executor] Saved campaign {campaign_id} to DB")
    finally:
        db.close()



# ═══════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def execute_campaigns(state, llm, log_callback=None):
    succeeded = []
    failed = []

    for segment_label, variant in state.variants_to_execute.items():
        customer_ids = state.all_segments.get(segment_label, [])
        if not customer_ids:
            continue

        task = (
            f"Send an email campaign to {len(customer_ids)} customers in the "
            f"'{segment_label}' segment. The email subject is: '{variant['subject']}'. "
            f"I need to submit this campaign to the CampaignX API."
        )

        # LLM dynamically selects the tool
        try:
            tool_decision = _discover_tool_via_llm(llm, task, log_callback)
        except Exception as e:
            if log_callback:
                log_callback(f"Tool discovery failed for {segment_label}: {e}")
            failed.append(segment_label)
            continue

        # Build parameters from variant data
        params = {
            "subject": variant["subject"],
            "body": variant["body"],
            "list_customer_ids": customer_ids,
            "send_time": variant.get("send_time", state.send_time)
        }

        # Execute via api_tools.py with retry
        result = None
        for attempt in range(2):
            try:
                result = call_tool_by_name(tool_decision["tool_name"], params)
                if result and result.get("response_code") in [200, 201]:
                    succeeded.append({
                        "segment_label": segment_label,
                        "variant_label": variant["variant_label"],
                        "api_campaign_id": result.get("campaign_id"),
                        "customers_sent": len(customer_ids)
                    })
                    break
            except Exception as e:
                if attempt == 0:
                    if log_callback:
                        log_callback(f"Send attempt 1 failed for {segment_label}, retrying...")
                else:
                    if log_callback:
                        log_callback(f"Send failed after retry for {segment_label}: {e}")
                    failed.append(segment_label)

    if log_callback:
        log_callback(
            f"Executed {len(succeeded)} campaigns successfully, {len(failed)} failed"
        )

    state.execution_results = {"succeeded": succeeded, "failed": failed}
    return state


# ── Logging ───────────────────────────────────────────────────────────────

def _log_to_db(campaign_id: str, iteration: int, sent: list[dict], failed: list[dict]) -> None:
    """Log the execution summary to agent_logs."""
    import json as _json
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog

    campaign_ids = [s.get("api_campaign_id", s["campaign_id"]) for s in sent]
    msg = _json.dumps({
        "iteration": iteration,
        "variant_count": len(sent) + len(failed),
        "sent_count": len(sent),
        "failed_count": len(failed),
        "campaign_ids": campaign_ids,
        "api_campaign_ids": campaign_ids,
        "reasoning": f"Executed {len(sent)} campaigns successfully, {len(failed)} failed",
    })

    db = SessionLocal()
    try:
        log = AgentLog(
            created_at=datetime.now(timezone.utc),
            campaign_id=campaign_id,
            agent_name="executor",
            message=msg,
        )
        db.add(log)
        db.commit()
        print("[executor] Logged to agent_logs table")
    finally:
        db.close()
