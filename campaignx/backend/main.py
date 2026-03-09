"""
backend/main.py
FastAPI server wiring all agents into REST endpoints.

Long-running endpoints (/start, /decision) return 202 immediately and
run the orchestrator in the background. The frontend polls /status to
track progress.

Endpoints:
  POST /api/campaign/start            — Launch a new campaign pipeline (202)
  POST /api/campaign/{id}/decision    — Approve or reject variants (202)
  GET  /api/campaign/{id}/status      — Poll campaign state
  GET  /api/cohort/summary            — Cohort schema summary
  GET  /api/tools                     — Discovered API tools
  GET  /api/budget                    — API budget status
  GET  /health                        — Health check
"""
import asyncio
import uuid
from dataclasses import asdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.db.session import init_db
from backend.agents.orchestrator import (
    Orchestrator,
    CampaignState,
    get_state,
    save_state,
)
from backend.agents.profiler import CustomerProfiler
from backend.tools.api_tools import (
    call_tool_by_name,
    get_tool_descriptions,
    get_budget_status,
)


# ═══════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════

class StartCampaignRequest(BaseModel):
    campaign_brief: str
    max_iterations: int = 3


class DecisionRequest(BaseModel):
    decision: str       # "approve" or "reject"
    feedback: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    init_db()
    print("[main] Database initialized")
    yield


app = FastAPI(
    title="CampaignX",
    description="AI-powered email campaign orchestrator for SuperBFSI",
    version="2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single orchestrator instance
orchestrator = Orchestrator()


# ═══════════════════════════════════════════════════════════════════════════
# BACKGROUND TASK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

async def _run_campaign(campaign_id: str, state: CampaignState):
    """Background: run the full pipeline until awaiting_approval or error."""
    try:
        state = await orchestrator.run(campaign_id, state)
        save_state(campaign_id, state)
    except Exception as e:
        state.status = "error"
        state.error = str(e)
        save_state(campaign_id, state)
        print(f"[main] Background _run_campaign error: {e}")


async def _resume_campaign(
    campaign_id: str,
    state: CampaignState,
    decision: str,
    feedback: str,
):
    """Background: resume after human decision."""
    try:
        state = await orchestrator.resume(campaign_id, state, decision, feedback)
        save_state(campaign_id, state)
    except Exception as e:
        state.status = "error"
        state.error = str(e)
        save_state(campaign_id, state)
        print(f"[main] Background _resume_campaign error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _state_to_dict(state: CampaignState) -> dict:
    """
    Serialize CampaignState to a JSON-safe dict.
    Excludes _profiler and cohort_ids (not JSON serializable).
    Converts Segment objects in all_segments.
    """
    d = {}
    for field_name in state.__dataclass_fields__:
        # Skip non-serializable fields
        if field_name in ("_profiler", "cohort_ids", "cached_cohort"):
            continue
        val = getattr(state, field_name)
        # Convert sets to lists for JSON
        if isinstance(val, set):
            val = list(val)
        # Convert Segment objects in all_segments dict
        if field_name == "all_segments" and isinstance(val, dict):
            val = {
                label: {
                    "label": seg.label,
                    "description": seg.description,
                    "size": seg.size,
                    "priority": seg.priority,
                    "is_catch_all": seg.is_catch_all,
                    "recommended_tone": seg.recommended_tone,
                    "recommended_send_hour": seg.recommended_send_hour,
                    "key_usp": seg.key_usp,
                    "persona_hint": seg.persona_hint,
                }
                for label, seg in val.items()
                if hasattr(seg, "label")
            }
        d[field_name] = val
    return d


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

# ── POST /api/campaign/start ─────────────────────────────────────────────

@app.post("/api/campaign/start", status_code=202)
async def start_campaign(req: StartCampaignRequest):
    """
    Start a new campaign pipeline.
    Returns 202 immediately. Pipeline runs in background.
    Frontend polls GET /api/campaign/{id}/status to track progress.
    """
    try:
        campaign_id = str(uuid.uuid4())
        state = CampaignState(
            campaign_brief=req.campaign_brief,
            max_iterations=req.max_iterations,
        )
        state.status = "starting"
        save_state(campaign_id, state)

        # Launch background task
        asyncio.create_task(_run_campaign(campaign_id, state))

        return {"campaign_id": campaign_id, "status": "starting"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /api/campaign/{campaign_id}/decision ────────────────────────────

@app.post("/api/campaign/{campaign_id}/decision", status_code=202)
async def campaign_decision(campaign_id: str, req: DecisionRequest):
    """
    Approve or reject pending variants.
    Returns 202 immediately. Execution runs in background.
    """
    try:
        state = get_state(campaign_id)
        if state is None:
            raise HTTPException(
                status_code=404,
                detail=f"Campaign {campaign_id} not found",
            )

        if state.status != "awaiting_approval":
            raise HTTPException(
                status_code=400,
                detail=f"Campaign is in '{state.status}' state, not 'awaiting_approval'",
            )

        state.status = "processing"
        save_state(campaign_id, state)

        # Launch background task
        asyncio.create_task(
            _resume_campaign(campaign_id, state, req.decision, req.feedback)
        )

        return {"campaign_id": campaign_id, "status": "processing"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/campaign/{campaign_id}/status ───────────────────────────────

@app.get("/api/campaign/{campaign_id}/status")
async def campaign_status(campaign_id: str):
    """Get the full current state of a campaign (poll endpoint)."""
    try:
        from backend.db.session import SessionLocal
        from backend.db.models import AgentLog, Campaign, CampaignReport
        import json

        state = get_state(campaign_id)
        if state is not None:
            state_dict = _state_to_dict(state)

            # Map agent_logs from DB
            db = SessionLocal()
            try:
                logs = db.query(AgentLog).filter(AgentLog.campaign_id == campaign_id).order_by(AgentLog.created_at.asc()).all()
                if logs and logs[0].created_at:
                    state_dict["start_date"] = logs[0].created_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    state_dict["start_date"] = ""
                
                agent_logs_formatted = []
                for log in logs:
                    try:
                        msg_data = json.loads(log.message)
                        action = msg_data.get("reasoning", "Action logged.")
                    except:
                        action = log.message

                    agent_logs_formatted.append({
                        "timestamp": log.created_at.strftime("%H:%M:%S") if log.created_at else "",
                        "agent_name": log.agent_name,
                        "action": action
                    })
                
                state_dict["agent_logs"] = agent_logs_formatted
            finally:
                db.close()

            return state_dict

        # Not in active memory -> Check SQLite Database Fallback
        db = SessionLocal()
        try:
            # First try direct match
            campaigns = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).all()
            
            # If not found directly, it might be the overarching ID linked via agent logs
            if not campaigns:
                executor_logs = db.query(AgentLog).filter(AgentLog.campaign_id == campaign_id, AgentLog.agent_name == "executor").all()
                sub_ids = []
                for log in executor_logs:
                    try:
                        data = json.loads(log.message)
                        sub_ids.extend(data.get("campaign_ids", []))
                    except:
                        pass
                if sub_ids:
                    campaigns = db.query(Campaign).filter(Campaign.campaign_id.in_(sub_ids)).all()
            
            logs = db.query(AgentLog).filter(AgentLog.campaign_id == campaign_id).order_by(AgentLog.created_at.asc()).all()

            if not campaigns and not logs:
                raise HTTPException(
                    status_code=404,
                    detail=f"Campaign {campaign_id} not found",
                )
            
            # 1. Status
            status = "done"

            # 2. Brief
            brief = campaigns[0].subject if campaigns else "Campaign generated by unknown source"
            parser_log = next((l for l in logs if l.agent_name == "brief_parser"), None)
            if parser_log:
                try:
                    data = json.loads(parser_log.message)
                    brief = data.get("input", {}).get("campaign_brief", brief)
                except:
                    pass

            # 3. Segments (segment_label is now comma-separated in single row)
            segments = []
            if campaigns:
                for c in campaigns:
                    segments.extend([s.strip() for s in c.segment_label.split(",") if s.strip()])
                segments = list(set(segments))

            # 4. all_results
            all_results = []
            total_global_opens = 0
            total_global_clicks = 0
            total_global_sent = 0

            if campaigns:
                all_reports = db.query(
                    CampaignReport, Campaign.segment_label, Campaign.variant_label
                ).join(
                    Campaign, Campaign.campaign_id == CampaignReport.campaign_id
                ).filter(
                    Campaign.campaign_id.in_([c.campaign_id for c in campaigns])
                ).all()

                results_map = {}
                for report, seg_label, var_label in all_reports:
                    key = (seg_label, var_label)
                    if key not in results_map:
                        results_map[key] = {"opens": 0, "clicks": 0, "total": 0}
                    results_map[key]["total"] += 1
                    if report.email_opened == "Y":
                        results_map[key]["opens"] += 1
                    if report.email_clicked == "Y":
                        results_map[key]["clicks"] += 1
                
                for (seg_label, var_label), stats in results_map.items():
                    t = stats["total"]
                    o = stats["opens"]
                    c = stats["clicks"]
                    o_rate = o / t if t > 0 else 0.0
                    c_rate = c / t if t > 0 else 0.0
                    comp = (o_rate * 0.4) + (c_rate * 0.6)
                    
                    total_global_opens += o
                    total_global_clicks += c
                    total_global_sent += t

                    all_results.append({
                        "segment_label": seg_label,
                        "variant_label": var_label,
                        "open_rate": o_rate,
                        "click_rate": c_rate,
                        "composite_score": comp,
                        "total_sent": t,
                        "opens": o,
                        "clicks": c
                    })

                if not all_results:
                    for c in campaigns:
                        sent_cnt = len(c.customer_ids) if c.customer_ids else 0
                        total_global_sent += sent_cnt
                        all_results.append({
                            "segment_label": c.segment_label,
                            "variant_label": c.variant_label,
                            "open_rate": 0.0,
                            "click_rate": 0.0,
                            "composite_score": 0.0,
                            "total_sent": sent_cnt,
                            "opens": 0,
                            "clicks": 0
                        })

            # 5. logs
            agent_logs_formatted = []
            for log in logs:
                try:
                    msg_data = json.loads(log.message)
                    action = msg_data.get("reasoning", "Action logged.")
                except:
                    action = log.message
                agent_logs_formatted.append({
                    "timestamp": log.created_at.strftime("%H:%M:%S") if log.created_at else "",
                    "agent_name": log.agent_name,
                    "action": action
                })
            
            # 6. final_summary
            best_overall = max(all_results, key=lambda x: x["composite_score"]) if all_results else {}
            
            final_summary = {
                "total_campaigns_sent": len(campaigns) if campaigns else 0,
                "total_customers_reached": total_global_sent,
                "iterations_completed": max([c.iteration for c in campaigns] + [0]) if campaigns else 0,
                "segments_targeted": segments,
                "best_overall": best_overall,
                "overall_open_rate": total_global_opens / total_global_sent if total_global_sent > 0 else 0.0,
                "overall_click_rate": total_global_clicks / total_global_sent if total_global_sent > 0 else 0.0,
            }

            started = ""
            if logs and logs[0].created_at:
                started = logs[0].created_at.strftime("%Y-%m-%d %H:%M:%S")
            elif campaigns:
                # Find log for this specific campaign? Wait, logs is already filtered by campaign_id.
                pass

            return {
                "campaign_id": campaign_id,
                "campaign_brief": brief,
                "status": status,
                "start_date": started,
                "segments_used": segments,
                "all_results": all_results,
                "final_summary": final_summary,
                "agent_logs": agent_logs_formatted,
                "iteration": max([c.iteration for c in campaigns] + [0]) if campaigns else 0,
                "optimization_notes": "",
                "pending_variants": []
            }

        except HTTPException:
            raise
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/campaigns ───────────────────────────────────────────────────

@app.get("/api/campaigns")
async def list_campaigns():
    """Get all campaigns (combining memory pool and database history)."""
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog, Campaign, CampaignReport
    from sqlalchemy import func
    from backend.agents.orchestrator import _active_states
    import json

    db = SessionLocal()
    try:
        campaigns_out = []
        seen_ids = set()

        # 1. In-memory stats (most recent/active)
        for cid, state in _active_states.items():
            seen_ids.add(cid)
            
            cust_sent = 0
            if state.sent_campaigns:
                cust_sent = sum(s.get("customer_count", 0) for s in state.sent_campaigns)
            
            open_rate = 0.0
            click_rate = 0.0
            if state.all_results:
                total_opens = sum(r.get("opens", 0) for r in state.all_results)
                total_clicks = sum(r.get("clicks", 0) for r in state.all_results)
                total_sent = sum(r.get("total_sent", 0) for r in state.all_results)
                if total_sent > 0:
                    open_rate = total_opens / total_sent
                    click_rate = total_clicks / total_sent
            
            started = ""
            first_log = db.query(AgentLog).filter(AgentLog.campaign_id == cid).order_by(AgentLog.created_at.asc()).first()
            if first_log and first_log.created_at:
                started = first_log.created_at.strftime("%Y-%m-%d %H:%M:%S")

            brief_snip = (state.campaign_brief[:80] + "...") if len(state.campaign_brief) > 80 else state.campaign_brief

            campaigns_out.append({
                "campaign_id": cid,
                "brief_snippet": brief_snip,
                "campaign_brief": brief_snip,  # included for frontend compatibility
                "status": state.status,
                "segments_count": len(state.segments_used) if state.segments_used else len(state.all_segments),
                "customers_sent": cust_sent,
                "open_rate": open_rate,
                "click_rate": click_rate,
                "created_at": started,
                "start_date": started,         # included for frontend compatibility
            })
            
        # 2. Database-only campaigns (historical)
        all_cids = db.query(AgentLog.campaign_id).distinct().all()
        for (cid,) in all_cids:
            if cid in seen_ids:
                continue
            
            first_log = db.query(AgentLog).filter(AgentLog.campaign_id == cid).order_by(AgentLog.created_at.asc()).first()
            parser_log = db.query(AgentLog).filter(AgentLog.campaign_id == cid, AgentLog.agent_name == "brief_parser").first()
            
            brief = "No brief available"
            if parser_log:
                try:
                    data = json.loads(parser_log.message)
                    brief = data.get("input", {}).get("campaign_brief", brief)
                except:
                    pass
            elif first_log:
                brief = "Campaign generated by unknown source"
                
            brief_snip = (brief[:80] + "...") if len(brief) > 80 else brief
            started = first_log.created_at.strftime("%Y-%m-%d %H:%M:%S") if first_log and first_log.created_at else ""
            
            # Count segments from comma-separated segment_label
            camp = db.query(Campaign).filter(Campaign.campaign_id == cid).first()
            segs = len([s.strip() for s in camp.segment_label.split(",") if s.strip()]) if camp else 0
            
            reports = db.query(CampaignReport).filter(CampaignReport.campaign_id == cid).all()
            cust_sent_reports = len(set(r.customer_id for r in reports))
            
            open_rate = 0.0
            click_rate = 0.0
            if cust_sent_reports > 0:
                opens = sum(1 for r in reports if r.email_opened == "Y")
                clicks = sum(1 for r in reports if r.email_clicked == "Y")
                open_rate = opens / cust_sent_reports
                click_rate = clicks / cust_sent_reports
                cust_sent = cust_sent_reports
            else:
                # Fallback to campaign intent if no reports
                camps = db.query(Campaign).filter(Campaign.campaign_id == cid).all()
                c_ids = set()
                for c in camps:
                    if c.customer_ids:
                        c_ids.update(c.customer_ids)
                cust_sent = len(c_ids)

            campaigns_out.append({
                "campaign_id": cid,
                "brief_snippet": brief_snip,
                "campaign_brief": brief_snip,
                "status": "done",
                "segments_count": segs,
                "customers_sent": cust_sent,
                "open_rate": open_rate,
                "click_rate": click_rate,
                "created_at": started,
                "start_date": started,
            })

        campaigns_out.sort(key=lambda x: x.get("created_at") or "9999-99-99", reverse=True)
        return {"campaigns": campaigns_out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ── DELETE /api/campaigns ────────────────────────────────────────────────

@app.delete("/api/campaigns")
async def delete_all_campaigns():
    """Delete all campaigns from the database and clear in-memory state."""
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog, Campaign, CampaignReport
    from backend.agents.orchestrator import _active_states

    db = SessionLocal()
    try:
        deleted_logs = db.query(AgentLog).delete()
        deleted_reports = db.query(CampaignReport).delete()
        deleted_campaigns = db.query(Campaign).delete()
        db.commit()

        _active_states.clear()

        return {
            "message": "All campaigns deleted",
            "deleted": {
                "agent_logs": deleted_logs,
                "campaign_reports": deleted_reports,
                "campaigns": deleted_campaigns,
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ── GET /api/cohort/summary ──────────────────────────────────────────────

_cohort_summary_cache = {}
_cohort_data_cache: list = []

@app.get("/api/cohort/summary")
async def cohort_summary():
    """Fetch cohort and return profiling summary."""
    global _cohort_summary_cache, _cohort_data_cache
    if _cohort_summary_cache:
        return _cohort_summary_cache

    try:
        from backend.db.session import SessionLocal
        from backend.db.models import CustomerCohort, Campaign, CampaignReport
        from backend.tools.api_tools import call_tool_by_name
        from collections import Counter
        
        db = SessionLocal()
        try:
            cohort_recs = db.query(CustomerCohort).all()
            if not cohort_recs:
                if _cohort_data_cache:
                    print("[cohort_summary] Using cached cohort data (no DB, no API call)")
                    api_data = _cohort_data_cache
                else:
                    print("[cohort_summary] No db records, fetching from API")
                    result = call_tool_by_name("get_customer_cohort")
                    api_data = result.get("data", [])
                    _cohort_data_cache = api_data
                
                # Normalize keys matching the DB row schema
                cohort_list = []
                for row in api_data:
                    cohort_list.append({
                        "city": row.get("City"),
                        "age": row.get("Age"),
                        "monthly_income": row.get("Monthly_Income"),
                        "gender": row.get("Gender")
                    })
            else:
                cohort_list = [{
                    "city": c.city, "age": c.age, "monthly_income": c.monthly_income, 
                    "gender": c.gender
                } for c in cohort_recs]
            
            if not cohort_list:
                return {}

            total_customers = len(cohort_list)
            
            cities = []
            ages = []
            incomes = []
            genders = []
            
            for c in cohort_list:
                cities.append(c.get("city", "Unknown"))
                ages.append(c.get("age", 0))
                incomes.append(c.get("monthly_income", 0))
                genders.append(c.get("gender", "Unknown"))
            
            total_cities = len(set(cities))
            average_age = sum(ages) / total_customers if total_customers else 0
            
            # Income Tiers: Low (<50000), Mid (50000-100000), High (>100000)
            def get_tier(inc):
                if inc < 50000: return "Low"
                if inc <= 100000: return "Mid"
                return "High"

            income_tiers = [get_tier(inc) for inc in incomes]
            dt_count = Counter(income_tiers)
            dominant_income_tier = dt_count.most_common(1)[0][0] if dt_count else "Unknown"
            
            # Gender split
            g_count = Counter(genders)
            gender_split = {
                k: {"count": v, "percentage": round(v / total_customers * 100, 1)}
                for k, v in g_count.items()
            }
            
            # Age distribution
            age_bins = {"18-24": 0, "25-34": 0, "35-44": 0, "45-54": 0, "55+": 0}
            for a in ages:
                if 18 <= a <= 24: age_bins["18-24"] += 1
                elif 25 <= a <= 34: age_bins["25-34"] += 1
                elif 35 <= a <= 44: age_bins["35-44"] += 1
                elif 45 <= a <= 54: age_bins["45-54"] += 1
                elif a >= 55: age_bins["55+"] += 1
            
            age_distribution = age_bins
            
            # Income distribution
            income_distribution = {
                "Low": {"count": dt_count.get("Low", 0), "percentage": round((dt_count.get("Low", 0)/total_customers*100) if total_customers else 0, 1)},
                "Mid": {"count": dt_count.get("Mid", 0), "percentage": round((dt_count.get("Mid", 0)/total_customers*100) if total_customers else 0, 1)},
                "High": {"count": dt_count.get("High", 0), "percentage": round((dt_count.get("High", 0)/total_customers*100) if total_customers else 0, 1)}
            }
            
            # Top cities
            c_count = Counter(cities)
            top_cities = []
            for city, count in c_count.most_common(10):
                top_cities.append({"name": city, "count": count, "percentage": round(count/total_customers*100, 1)})
                
            # Current segments
            # Query this from campaign_reports grouped by segment_label for the latest done campaign.
            # 1. find latest campaign
            latest_camp = db.query(Campaign).order_by(Campaign.created_at.desc()).first()
            current_segments = []
            if latest_camp:
                c_id = latest_camp.campaign_id
                # Get all segments for this campaign ID
                # Wait, the prompt says "Query this from campaign_reports grouped by segment_label for the latest done campaign."
                # But campaign_reports doesn't have segment_label. It has campaign_id and customer_id.
                # Campaign table has segment_label and customer_ids. 
                # Let's map customer to segment from Campaign
                all_camps = db.query(Campaign).filter(Campaign.campaign_id == c_id).all()
                cust_to_seg = {}
                for cp in all_camps:
                    if cp.customer_ids:
                        for cust in cp.customer_ids:
                            cust_to_seg[cust] = cp.segment_label
                
                reports = db.query(CampaignReport).filter(CampaignReport.campaign_id == c_id).all()
                seg_counts = Counter()
                for r in reports:
                    seg = cust_to_seg.get(r.customer_id)
                    if seg:
                        seg_counts[seg] += 1
                
                total_reports = len(reports)
                # If no reports yet, just use the campaign distribution
                if total_reports == 0:
                    for cp in all_camps:
                        cnt = len(cp.customer_ids) if cp.customer_ids else 0
                        seg_counts[cp.segment_label] += cnt
                    total_reports = sum(seg_counts.values())

                if total_reports > 0:
                    for seg, cnt in seg_counts.items():
                        current_segments.append({
                            "segment_label": seg,
                            "customer_count": cnt,
                            "percentage": round(cnt / total_reports * 100, 1)
                        })

            _cohort_summary_cache = {
                "total_customers": total_customers,
                "total_cities": total_cities,
                "average_age": round(average_age, 1),
                "dominant_income_tier": dominant_income_tier,
                "gender_split": gender_split,
                "age_distribution": age_distribution,
                "income_distribution": income_distribution,
                "top_cities": top_cities,
                "current_segments": current_segments
            }
            return _cohort_summary_cache
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/tools ───────────────────────────────────────────────────────

@app.get("/api/tools")
async def list_tools():
    """List all discovered CampaignX API tools."""
    try:
        return {"tools": get_tool_descriptions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/budget ──────────────────────────────────────────────────────

@app.get("/api/budget")
async def budget_status():
    """Get API budget status for today."""
    try:
        return get_budget_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /health ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "2.0"}


# ═══════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
