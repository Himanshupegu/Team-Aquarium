"""
agents/analyst.py
Fetches campaign reports, computes engagement metrics, and generates
LLM-driven strategic insight for the next iteration.

Single public function:
    analyze_performance(sent_campaigns, iteration) -> dict
"""
import json
from datetime import datetime, timezone

from backend.llm.router import llm_router
from backend.tools.api_tools import call_tool_by_name


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _is_yes(val) -> bool:
    """Flexible boolean check — handles Y, Yes, TRUE, 1, etc."""
    return str(val).strip().upper() in ("Y", "YES", "TRUE", "1")


def compute_metrics(report_rows: list[dict]) -> dict:
    """Compute open_rate, click_rate, and composite score from report rows."""
    total = len(report_rows)
    if total == 0:
        return {
            "open_rate": 0.0, "click_rate": 0.0, "composite_score": 0.0,
            "opens": 0, "clicks": 0, "total_sent": 0,
        }
    opens = sum(1 for r in report_rows if _is_yes(r.get("EO")))
    clicks = sum(1 for r in report_rows if _is_yes(r.get("EC")))
    open_rate = opens / total
    click_rate = clicks / total
    composite = round(click_rate * 0.7 + open_rate * 0.3, 4)
    return {
        "open_rate": round(open_rate, 4),
        "click_rate": round(click_rate, 4),
        "composite_score": composite,
        "opens": opens,
        "clicks": clicks,
        "total_sent": total,
    }


def save_report_to_db(campaign_id: str, report_rows: list[dict]) -> None:
    """Save every report row to campaign_reports table. Opens its own DB session."""
    from backend.db.session import SessionLocal
    from backend.db.models import CampaignReport

    db = SessionLocal()
    try:
        for row in report_rows:
            report = CampaignReport(
                campaign_id=campaign_id,
                customer_id=row.get("customer_id", ""),
                email_opened=row.get("EO", "N"),
                email_clicked=row.get("EC", "N"),
            )
            db.add(report)
        db.commit()
        print(f"[analyst] Saved {len(report_rows)} report rows for campaign {campaign_id}")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

async def analyze_performance(
    sent_campaigns: list[dict],
    iteration: int,
) -> dict:
    """
    Fetch reports for all sent campaigns, compute metrics, generate insight.

    Args:
        sent_campaigns: List of dicts from executor, each with:
            campaign_id, variant_label, segment_label, customer_count
        iteration: Campaign iteration number (1-based)

    Returns:
        {
            "results": [...],
            "best_variant": dict,
            "worst_variant": dict,
            "overall_open_rate": float,
            "overall_click_rate": float,
            "analyst_summary": str,
        }
    """
    results: list[dict] = []

    for campaign in sent_campaigns:
        campaign_id = campaign["campaign_id"]
        variant_label = campaign.get("variant_label", "?")
        segment_label = campaign.get("segment_label", "?")

        print(f"[analyst] Fetching report for campaign {campaign_id} "
              f"(variant={variant_label}, segment={segment_label})")

        # Fetch report from API
        report = call_tool_by_name("get_report", campaign_id=campaign_id)
        report_rows = report.get("data", [])

        if not report_rows:
            print(f"[analyst] WARNING: No report data for campaign {campaign_id}")

        # Save to DB
        save_report_to_db(campaign_id, report_rows)

        # Compute metrics
        metrics = compute_metrics(report_rows)
        result_entry = {
            "campaign_id": campaign_id,
            "variant_label": variant_label,
            "segment_label": segment_label,
            **metrics,
        }
        results.append(result_entry)

        print(f"[analyst] Campaign {campaign_id}: "
              f"open_rate={metrics['open_rate']}, click_rate={metrics['click_rate']}, "
              f"composite={metrics['composite_score']}")

    # Determine best and worst by composite score
    if results:
        best = max(results, key=lambda r: r["composite_score"])
        worst = min(results, key=lambda r: r["composite_score"])
    else:
        best = worst = {}

    # Overall metrics
    total_opens = sum(r["opens"] for r in results)
    total_clicks = sum(r["clicks"] for r in results)
    total_sent = sum(r["total_sent"] for r in results)
    overall_open_rate = round(total_opens / total_sent, 4) if total_sent else 0.0
    overall_click_rate = round(total_clicks / total_sent, 4) if total_sent else 0.0

    # Generate LLM insight
    analyst_summary = await _generate_insight(results, best, worst, iteration)

    output = {
        "results": results,
        "best_variant": best,
        "worst_variant": worst,
        "overall_open_rate": overall_open_rate,
        "overall_click_rate": overall_click_rate,
        "analyst_summary": analyst_summary,
    }

    # Log to DB
    _log_to_db(iteration, output)

    return output


# ═══════════════════════════════════════════════════════════════════════════
# LLM INSIGHT
# ═══════════════════════════════════════════════════════════════════════════

async def _generate_insight(
    results: list[dict],
    best: dict,
    worst: dict,
    iteration: int,
) -> str:
    """Ask the LLM for strategic reasoning about performance differences."""
    results_summary = json.dumps(results, indent=2)
    best_summary = json.dumps(best, indent=2)
    worst_summary = json.dumps(worst, indent=2)

    prompt = f"""You are a marketing performance analyst for SuperBFSI.

CAMPAIGN RESULTS (iteration {iteration}):
{results_summary}

BEST PERFORMING VARIANT:
{best_summary}

WORST PERFORMING VARIANT:
{worst_summary}

Do not restate the numbers. Explain the strategic reasoning — WHY one variant likely \
outperformed the other based on tone, subject length, emotional vs rational angle, or \
CTA placement. Give one concrete suggestion for the next iteration that is different \
from what was already tried.

Keep your response to 2-3 sentences maximum."""

    try:
        insight = await llm_router.call(prompt, task="reasoning", max_tokens=300)
        return insight.strip()
    except Exception as e:
        fallback = (
            f"Iteration {iteration}: Best variant was "
            f"{best.get('variant_label', '?')}/{best.get('segment_label', '?')} "
            f"(composite={best.get('composite_score', 0)}). "
            f"LLM insight unavailable: {e}"
        )
        print(f"[analyst] WARNING: LLM insight failed, using fallback: {e}")
        return fallback


# ═══════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════

def _log_to_db(iteration: int, output: dict) -> None:
    """Log the analysis results to agent_logs."""
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog

    db = SessionLocal()
    try:
        log = AgentLog(
            timestamp=datetime.now(timezone.utc),
            agent_name="analyst",
            iteration=iteration,
            input_data={
                "campaign_count": len(output.get("results", [])),
            },
            output_data={
                "overall_open_rate": output["overall_open_rate"],
                "overall_click_rate": output["overall_click_rate"],
                "best_variant": output["best_variant"].get("variant_label", "?"),
                "worst_variant": output["worst_variant"].get("variant_label", "?"),
                "result_count": len(output["results"]),
            },
            reasoning=output.get("analyst_summary", ""),
        )
        db.add(log)
        db.commit()
        print("[analyst] Logged to agent_logs table")
    finally:
        db.close()
