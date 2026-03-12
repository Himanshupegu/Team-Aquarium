"""
agents/executor.py
Sends approved campaign variants via the CampaignX API and saves results to DB.

Single public function:
    execute_campaigns(variants, iteration, cohort_ids) -> dict

Returns: {"sent": [...], "failed": [...]}
"""
from datetime import datetime, timedelta, timezone

from backend.tools.api_tools import call_tool_by_name

IST = timezone(timedelta(hours=5, minutes=30))


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

async def execute_campaigns(
    campaign_id: str,
    variants: list[dict],
    iteration: int,
    cohort_ids: set[str],
) -> dict:
    """
    Send approved campaign variants via the CampaignX API.

    Args:
        campaign_id: The main campaign ID for this execution.
        variants: List of dicts, each with keys:
            variant_label, segment_label, subject, body,
            customer_ids (list), send_time (str), strategy_notes
        iteration: Campaign iteration number (1-based)
        cohort_ids: Set of all valid customer IDs from the cohort

    Returns:
        {"sent": [{"campaign_id", "variant_label", "segment_label", "customer_count"}],
         "failed": [{"variant_label", "error"}]}
    """
    sent: list[dict] = []
    failed: list[dict] = []
    all_customer_ids: list[str] = []
    segment_labels: list[str] = []

    for variant in variants:
        variant_label = variant.get("variant_label", "?")
        segment_label = variant.get("segment_label", "?")

        try:
            # Sanitize customer IDs
            raw_ids = variant.get("customer_ids", [])
            clean_ids = sanitize_customer_ids(raw_ids, cohort_ids)

            if not clean_ids:
                msg = f"No valid customer IDs remaining after sanitization"
                print(f"[executor] Skipping variant {variant_label}/{segment_label}: {msg}")
                failed.append({"variant_label": variant_label, "error": msg})
                continue

            subject = variant.get("subject", "")
            body = variant.get("body", "")
            send_time = variant.get("send_time", "")
            strategy_notes = variant.get("strategy_notes", "")

            print(f"[executor] Sending variant {variant_label} for '{segment_label}' "
                  f"({len(clean_ids)} customers, send_time={send_time})")

            # Call the CampaignX API via dynamically discovered tool
            # Add one automatic retry for failed sends
            result = {}
            last_error = None
            for attempt in range(2): # 0, 1 -> max 2 attempts
                try:
                    result = call_tool_by_name(
                        "send_campaign",
                        subject=subject,
                        body=body,
                        list_customer_ids=clean_ids,
                        send_time=send_time,
                    )
                    # Check for API errors
                    response_code = result.get("response_code", 0)
                    if response_code in (200, 201):
                        break # Success
                    
                    error_msg = result.get("message", result.get("detail", str(result)))
                    print(f"[executor] API error for {variant_label} on attempt {attempt + 1}: {error_msg}")
                    last_error = str(error_msg)
                except Exception as e:
                    print(f"[executor] ERROR sending variant {variant_label} on attempt {attempt + 1}: {type(e).__name__}: {e}")
                    last_error = str(e)
                    result = {} # Ensure result is dict
                    
                if attempt == 0:
                    print(f"[executor] Retrying send_campaign for {variant_label}...")

            response_code = result.get("response_code", 0)
            if response_code not in (200, 201):
                failed.append({"variant_label": variant_label, "error": last_error or "Unknown error"})
                continue

            api_campaign_id = result.get("campaign_id", "")
            if not api_campaign_id:
                print(f"[executor] WARNING: No campaign_id in response for {variant_label}")
                failed.append({"variant_label": variant_label, "error": "No campaign_id in response"})
                continue

            all_customer_ids.extend(clean_ids)
            if segment_label not in segment_labels:
                segment_labels.append(segment_label)

            sent.append({
                "campaign_id": campaign_id,          # orchestrator's ID
                "api_campaign_id": api_campaign_id,  # API-returned ID for reports
                "variant_label": variant_label,
                "segment_label": segment_label,
                "customer_count": len(clean_ids),
            })
            print(f"[executor] ✓ Campaign sent (api_id={api_campaign_id})")

        except Exception as e:
            print(f"[executor] ERROR sending variant {variant_label}: {type(e).__name__}: {e}")
            failed.append({"variant_label": variant_label, "error": str(e)})

    # Save one Campaign row for this orchestrator run
    if sent:
        first_variant = variants[0] if variants else {}
        save_campaign_to_db(
            campaign_id=campaign_id,
            iteration=iteration,
            segment_labels=segment_labels,
            subject=first_variant.get("subject", ""),
            body=first_variant.get("body", ""),
            customer_ids=all_customer_ids,
            send_time=first_variant.get("send_time", ""),
            strategy_notes=first_variant.get("strategy_notes", ""),
        )

    # Log summary to agent_logs
    _log_to_db(campaign_id, iteration, sent, failed)

    print(f"[executor] Execution complete — {len(sent)} sent, {len(failed)} failed")
    return {"sent": sent, "failed": failed}


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
