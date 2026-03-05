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
        updated = await orchestrator.run(state)
        save_state(campaign_id, updated)
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
        updated = await orchestrator.resume(state, decision, feedback)
        save_state(campaign_id, updated)
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
        if field_name in ("_profiler", "cohort_ids"):
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
        state = get_state(campaign_id)
        if state is None:
            raise HTTPException(
                status_code=404,
                detail=f"Campaign {campaign_id} not found",
            )

        return _state_to_dict(state)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/cohort/summary ──────────────────────────────────────────────

@app.get("/api/cohort/summary")
async def cohort_summary():
    """Fetch cohort and return profiling summary."""
    try:
        result = call_tool_by_name("get_customer_cohort")
        cohort = result.get("data", [])
        profiler = CustomerProfiler(cohort)
        return profiler.summary()

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
