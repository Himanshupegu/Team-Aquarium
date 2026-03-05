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
        _log_to_db(iteration, result)
        return result

    # ── Continue: select next segments ──────────────────────────────────

    next_segments = _select_next_segments(
        all_segments, segments_used, all_results, max_pick=2,
    )

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

    _log_to_db(iteration, result)
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
    First priority: unused segments, largest first.
    Second priority: re-target worst performer from last iteration.
    """
    used_set = set(segments_used)

    # Unused segments sorted by size (largest first)
    unused = [
        (label, seg) for label, seg in all_segments.items()
        if label not in used_set
    ]
    unused.sort(key=lambda x: x[1].size, reverse=True)

    next_labels = [label for label, _ in unused[:max_pick]]

    # If all used but we haven't hit max_iterations, re-target worst performer
    if not next_labels and all_results:
        worst = min(all_results, key=lambda r: r.get("composite_score", 999))
        worst_label = worst.get("segment_label", "")
        if worst_label and worst_label in all_segments:
            next_labels = [worst_label]
            print(f"[optimizer] All segments used — re-targeting worst performer: {worst_label}")

    print(f"[optimizer] Next segments: {next_labels}")
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


def _log_to_db(iteration: int, result: dict) -> None:
    """Log optimizer decision to agent_logs."""
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog

    db = SessionLocal()
    try:
        log = AgentLog(
            timestamp=datetime.now(timezone.utc),
            agent_name="optimizer",
            iteration=iteration,
            input_data={
                "should_continue": result["should_continue"],
                "next_segments": result["next_segments"],
                "stop_reason": result.get("stop_reason"),
            },
            output_data={
                "optimization_notes": result["optimization_notes"][:500],
            },
            reasoning=f"{'Continuing' if result['should_continue'] else 'Stopping'}: "
                      f"{result.get('stop_reason', 'targeting ' + str(result['next_segments']))}",
        )
        db.add(log)
        db.commit()
        print("[optimizer] Logged to agent_logs table")
    finally:
        db.close()
