# CampaignX — AI Multi-Agent System for Marketing Campaign Automation

**Built for FrostHack | XPECTO 2026 by InXiteOut | IIT Mandi**

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![LangGraph](https://img.shields.io/badge/LangGraph-Enabled-orange)
![SQLite](https://img.shields.io/badge/SQLite-Database-blue)

## Team
**Team Name:** Team Aquarium  
**Members:** Himanshu Pegu, Shikhin Sharma, Siddharth Singh, and Vishal Singh

## Project Overview
CampaignX is an AI-powered multi-agent system that takes a natural language campaign brief, autonomously profiles 5,000 customers into segments, and generates personalised A/B email variants per segment. It then executes campaigns via API, fetches performance reports immediately, and runs an autonomous optimization loop to continuously improve results. A human-in-the-loop approval mechanism ensures safe execution at each iteration.

## Architecture
The CampaignX system operates through a full agent pipeline in the following order:
1. **brief_parser**: Extracts key parameters, objectives, and constraints from the natural language brief.
2. **profiler**: Analyzes the cohort schema and dynamically defines mutually exclusive customer segments.
3. **content_gen**: Generates personalized, emotionally and rationally engaging A/B email variants for each segment.
4. **executor**: Dispatches the finalized campaign content to the deployment API.
5. **analyst**: Ingests and evaluates performance data from the executed campaigns.
6. **optimizer**: Re-targets the worst-performing segments to improve overall KPI results in subsequent iterations.
7. **orchestrator**: Manages the overarching state, workflow transitions, and human-in-the-loop approvals.

**Supporting Layers:**
- `api_tools.py`: Enables dynamic OpenAPI spec discovery for tool integration without hardcoded endpoints.
- `llm/router.py`: Implements an intelligent LLM fallback chain starting from Gemini, falling back to Groq, and then Mistral.
- **SQLite Database**: Manages state using four tables: `campaigns`, `campaign_reports`, `agent_logs`, and `api_usage_tracker`.

## Key Technical Highlights
- **Dynamic tool discovery:** All API tools are discovered at runtime from the live OpenAPI spec, no hardcoded endpoints.
- **LLM-driven segmentation:** The profiler analyses cohort schema and asks the LLM to define 4-9 mutually exclusive segments dynamically.
- **Autonomous optimization loop:** Optimizer re-targets worst-performing segments when all segments have been covered, runs until `max_iterations`.
- **Human-in-the-loop:** Orchestrator pauses at `awaiting_approval` state, frontend polls for this, user approves or rejects with feedback.
- **Background task architecture:** FastAPI endpoints return 202 immediately, orchestrator runs in background, frontend polls status endpoint every 3 seconds.
- **A/B testing:** Every segment gets a rational variant A and an emotional variant B, composite score = click_rate × 0.7 + open_rate × 0.3.

## Tech Stack
- **Backend:** Python 3.11, FastAPI, LangGraph, SQLAlchemy, SQLite, Uvicorn
- **Frontend:** Next.js 14, Tailwind CSS, TypeScript
- **LLMs:** Gemini 2.0 Flash Lite (primary), Groq llama-3.3-70b-versatile (fallback 1), Mistral Small (fallback 2)
- **Other:** httpx, jsonref, python-dotenv

## Project Structure
```text
campaignx/
├── backend/
│   ├── agents/          # LangGraph agents for parsing, optimizing, etc.
│   ├── tools/           # Dynamic API spec discovery and tool functions
│   ├── llm/             # LLM router with fallback chain (Gemini/Groq/Mistral)
│   ├── db/              # Database schema and SQLAlchemy setup
│   ├── main.py          # FastAPI application entry point
├── frontend/            # Next.js frontend application
├── tests/               # Pytest suite for API endpoints and agents
├── requirements.txt     # Python dependencies
└── .env.example         # Template for environment variables
```

## Prerequisites
- Python 3.11+
- Node.js 18+
- `pip`
- `npm`

**API keys required:** `GEMINI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, `CAMPAIGNX_API_KEY`, `CAMPAIGNX_TEAM_NAME`.

## Setup and Installation
Follow these step-by-step instructions to get the project running locally:

1. Clone the repo:
   ```bash
   git clone <repository-url>
   cd campaignx
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Open .env and fill in your API keys
   ```
5. Initialize the database:
   ```bash
   python -m backend.db.init_db
   ```
6. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

## Running the Application
To run the full application, open two terminals and run the following commands side-by-side:

**Terminal 1 (Backend - Port 8000):**
```bash
python -m uvicorn backend.main:app --reload
```

**Terminal 2 (Frontend - Port 3000):**
```bash
cd frontend
npm run dev
```
Then, open your browser and navigate to [http://localhost:3000](http://localhost:3000).

## Running Tests
Run the following test commands in order, one per sub-phase. 

*Note: Setting `MOCK_API=true` skips live API calls and uses mock data. `MOCK_API=false` uses real network calls. Tests requiring the backend server to be running are noted below.*

```bash
# Phase 1
pytest tests/test_phase1_sub1.py
pytest tests/test_phase1_sub_2_3.py

# Phase 2
pytest tests/test_phase2_sub4_to_6.py
pytest tests/test_phase2_sub7.py
pytest tests/test_phase2_sub8.py

# Phase 3
pytest tests/test_phase3_parta.py  # MOCK_API=false required.
pytest tests/test_phase3_partb.py  # Requires server running.
pytest tests/test_phase3_partc.py  # Requires server running.
```

## Environment Variables
The application requires the following environment variables, detailed in `.env.example`:

| Variable Name | Description | Example Value |
| --- | --- | --- |
| `GEMINI_API_KEY` | Primary LLM API key for Gemini 2.0 Flash Lite | `AIzaSyB...` |
| `GROQ_API_KEY` | Fallback 1 LLM API key for Groq | `gsk_...` |
| `MISTRAL_API_KEY` | Fallback 2 LLM API key for Mistral | `mistral_...` |
| `CAMPAIGNX_API_KEY` | API key for deployment operations | `camp_...` |
| `CAMPAIGNX_TEAM_NAME` | Assigned team name for tracking | `Team Aquarium` |
| `DATABASE_URL` | SQLite database connection string | `sqlite:///./campaignx.db` |
| `MOCK_API` | Flag to enable/disable external API mocking | `true` or `false` |
| `NEXT_PUBLIC_API_URL` | Base URL for the frontend to connect to backend | `http://localhost:8000` |

## API Endpoints
The following FastAPI endpoints are exposed:

| Method | Path | Description | Response Code |
| --- | --- | --- | --- |
| POST | `/api/campaign/start` | Initiates a new campaign orchestration process. | 202 Accepted |
| POST | `/api/campaign/{id}/decision` | Submits human-in-the-loop approval/rejection for an iteration. | 202 Accepted |
| GET | `/api/campaign/{id}/status` | Polls the current state/progress of a specific campaign. | 200 OK |
| GET | `/api/cohort/summary` | Retrieves analytical summaries and definitions of target cohorts. | 200 OK |
| GET | `/api/tools` | Discovers and returns available API tools dynamically mapped. | 200 OK |
| GET | `/api/budget` | Retrieves current campaign budget usage metrics. | 200 OK |
| GET | `/health` | Basic health check for application status monitoring. | 200 OK |

## Hackathon Compliance
- [x] **Dynamic API discovery:** Live OpenAPI spec parsing.
- [x] **Human-in-loop:** Pause at `awaiting_approval` for user review.
- [x] **A/B testing:** Rational A and emotional B variants evaluated per segment.
- [x] **Autonomous optimization loop:** Iterative improvements with `max_iterations`.
- [x] **LLM-driven segmentation:** Mutually exclusive target segmenting using intelligent context profiling.
- [x] **Agent logging:** Traceable decisions across LangGraph pipeline mapped in SQLite database.
- [x] **Composite score formula:** Formula execution (click 70%, open 30%) across variants.
- [x] **Full cohort coverage across iterations:** Every valid cohort is evaluated until full conversion.
