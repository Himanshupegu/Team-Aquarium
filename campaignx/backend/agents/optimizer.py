"""
agents/optimizer.py
Decides whether to continue the campaign loop and which segments to target next.

Single public function:
    decide_next_iteration(all_results, segments_used, all_segments,
                          iteration, max_iterations, campaign_brief) -> dict
"""
import json
from datetime import datetime, timezone

from backend.llm.router import llm_router


# ═══════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

async def decide_next_iteration(
    campaign_id: str,
    all_results: list[dict],
    segments_used: list[str],
    all_segments: dict,
    iteration: int,
    max_iterations: int,
    campaign_brief: dict,
) -> dict:
    """
    Analyze cumulative results and decide whether to continue the campaign loop.

    Args:
        campaign_id: The ID of the current campaign.
        all_results: Cumulative results across all iterations
                     (each entry has composite_score, variant_label, segment_label, etc.)
        segments_used: Segment labels already targeted in previous iterations
        all_segments: Full segment dict from profiler (label -> Segment)
        iteration: Current iteration number (1-based)
        max_iterations: Maximum allowed iterations
        campaign_brief: Parsed brief dict

    Returns:
        {
            "should_continue": bool,
            "next_segments": list[str],
            "optimization_notes": str,
            "stop_reason": str | None,
        }
    """
    # ── Stop condition: max iterations only ─────────────────────────────
    # Design: the optimizer should react to failure, not give up.
    # A 0.0 score is when the loop should try harder, not quit.

    if iteration >= max_iterations:
        result = _build_stop_result("max_iterations_reached",
                                    f"Reached maximum of {max_iterations} iterations")
        result["optimization_notes"] = await _generate_notes(
            iteration, True, "max_iterations_reached",
            segments_used, [], all_results,
        )
        _log_to_db(campaign_id, iteration, result)
        return result

    # ── Continue: select next segments ──────────────────────────────────
    if iteration > 1:
        _filter_converted_users(campaign_id, all_segments)

    max_pick_val = len(all_segments) if iteration == 1 else 2
    next_segments = _select_next_segments(
        all_segments, segments_used, all_results, max_pick=max_pick_val,
    )

    if not next_segments:
        result = _build_stop_result("no_viable_segments", "No segments met retargeting thresholds (minimum 10 unconverted users)")
        result["optimization_notes"] = await _generate_notes(
            iteration, True, result["stop_reason"],
            segments_used, [], all_results,
        )
        _log_to_db(campaign_id, iteration, result)
        return result

    optimization_notes = await _generate_notes(
        iteration, False, None,
        segments_used, next_segments, all_results,
    )

    result = {
        "should_continue": True,
        "next_segments": next_segments,
        "optimization_notes": optimization_notes,
        "stop_reason": None,
    }

    _log_to_db(campaign_id, iteration, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# SEGMENT SELECTION
# ═══════════════════════════════════════════════════════════════════════════

def _select_next_segments(
    all_segments: dict,
    segments_used: list[str],
    all_results: list[dict],
    max_pick: int = 2,
) -> list[str]:
    """
    Pick next segments to target.
    First priority: segments targeted the fewest number of times, largest first.
    Second priority: if all segments have been targeted at least once, re-target worst performer among those with fewest targets.
    """
    if not all_segments:
        return []

    # Count how many times each segment has been used, considering only known segments
    counts = {label: 0 for label in all_segments}
    for label in segments_used:
        if label in counts:
            counts[label] += 1

    # Find the minimum usage count
    min_count = min(counts.values())

    # Get all segments with this minimum count
    candidate_labels = {label for label, count in counts.items() if count == min_count}

    # First try picking largest from candidates if min_count == 0 (completely unused)
    if min_count == 0:
        candidates = [(label, all_segments[label]) for label in candidate_labels]
        candidates.sort(key=lambda x: x[1].size, reverse=True)
        next_labels = [label for label, _ in candidates[:max_pick]]
        print(f"[optimizer] Next segments (unused): {next_labels}")
        return next_labels

    # If min_count > 0, we are re-targeting. Pick segments with most unconverted users.
    candidates = [(label, all_segments[label]) for label in candidate_labels if label in all_segments]
    
    # Filter candidates with < 10 unconverted customers for retargeting
    candidates = [(label, seg) for label, seg in candidates if len(seg.customer_ids) >= 10]

    # size reflects exact unconverted count since converted users were filtered out
    candidates.sort(key=lambda x: len(x[1].customer_ids), reverse=True)
    next_labels = [label for label, _ in candidates[:max_pick]]

    print(f"[optimizer] Next segments (re-targeted): {next_labels}")
    return next_labels


# ═══════════════════════════════════════════════════════════════════════════
# LLM NOTES
# ═══════════════════════════════════════════════════════════════════════════

async def _generate_notes(
    iteration: int,
    is_stopping: bool,
    stop_reason: str | None,
    segments_used: list[str],
    next_segments: list[str],
    all_results: list[dict],
) -> str:
    """Generate optimization reasoning via LLM. Falls back to simple string on failure."""
    # Summarize scores
    best_score = max((r.get("composite_score", 0) for r in all_results), default=0)
    worst_score = min((r.get("composite_score", 999) for r in all_results), default=0)
    best_entry = next((r for r in all_results if r.get("composite_score") == best_score), {})
    worst_entry = next((r for r in all_results if r.get("composite_score") == worst_score), {})

    decision = "STOPPING" if is_stopping else "CONTINUING"
    reason_text = f" Reason: {stop_reason}" if stop_reason else ""

    prompt = f"""You are a campaign optimization strategist for SuperBFSI.

Iteration: {iteration}
Decision: {decision}{reason_text}
Segments used so far: {segments_used}
Next segments to target: {next_segments if next_segments else 'None — campaign ending'}
Best composite score seen: {best_score} (variant={best_entry.get('variant_label', '?')}, segment={best_entry.get('segment_label', '?')})
Worst composite score seen: {worst_score} (variant={worst_entry.get('variant_label', '?')}, segment={worst_entry.get('segment_label', '?')})

In 2-3 sentences, explain why these next segments were chosen (or why the campaign is stopping) \
and what content angle to try differently in the next iteration. Be specific and actionable."""

    try:
        notes = await llm_router.call(prompt, task="reasoning", max_tokens=200)
        return notes.strip()
    except Exception as e:
        fallback = (
            f"Iteration {iteration}: {decision}.{reason_text} "
            f"Segments used: {segments_used}. Next: {next_segments}. "
            f"Best composite: {best_score}, worst: {worst_score}. "
            f"(LLM insight unavailable: {e})"
        )
        print(f"[optimizer] WARNING: LLM notes failed, using fallback: {e}")
        return fallback


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _build_stop_result(reason: str, detail: str) -> dict:
    """Build a stop result dict."""
    print(f"[optimizer] Stopping: {reason} — {detail}")
    return {
        "should_continue": False,
        "next_segments": [],
        "optimization_notes": "",  # will be filled by caller
        "stop_reason": reason,
    }


def _log_to_db(campaign_id: str, iteration: int, result: dict) -> None:
    """Log optimizer decision to agent_logs."""
    import json as _json
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog

    msg = _json.dumps({
        "iteration": iteration,
        "should_continue": result["should_continue"],
        "next_segments": result["next_segments"],
        "stop_reason": result.get("stop_reason"),
        "optimization_notes": result["optimization_notes"][:500],
        "reasoning": f"{'Continuing' if result['should_continue'] else 'Stopping'}: "
                     f"{result.get('stop_reason', 'targeting ' + str(result['next_segments']))}",
    })

    db = SessionLocal()
    try:
        log = AgentLog(
            created_at=datetime.now(timezone.utc),
            campaign_id=campaign_id,
            agent_name="optimizer",
            message=msg,
        )
        db.add(log)
        db.commit()
        print("[optimizer] Logged to agent_logs table")
    finally:
        db.close()


def _filter_converted_users(campaign_id: str, all_segments: dict) -> None:
    """Retargeting filter: exclude users who already had EO='Y' or EC='Y'."""
    from backend.db.session import SessionLocal
    from backend.db.models import CampaignReport
    from sqlalchemy import or_

    db = SessionLocal()
    converted_ids = set()
    try:
        reports = db.query(CampaignReport.customer_id).filter(
            CampaignReport.campaign_id == campaign_id,
            or_(CampaignReport.email_opened == 'Y', CampaignReport.email_clicked == 'Y')
        ).all()
        converted_ids = {r[0] for r in reports}
    except Exception as e:
        print(f"[optimizer] Error fetching converted users: {e}")
    finally:
        db.close()

    if not converted_ids:
        return

    for label, seg in all_segments.items():
        original_size = len(seg.customer_ids)
        seg.customer_ids = [cid for cid in seg.customer_ids if cid not in converted_ids]
        if len(seg.customer_ids) < original_size:
            print(f"[optimizer] Filtered {original_size - len(seg.customer_ids)} converted users from '{label}'")
