# CampaignX — AI Multi-Agent System for Marketing Campaign Automation

**Built for FrostHack | XPECTO 2026 by InXiteOut | IIT Mandi**

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![LangGraph](https://img.shields.io/badge/LangGraph-Enabled-orange)
![SQLite](https://img.shields.io/badge/SQLite-Database-blue)

## Team
**Team Name:** Team Aquarium  
**Members:** Himanshu Pegu, Shikhin Sharma, Siddharth Singh, Vishal Singh

---

## Project Overview
CampaignX is an AI-powered multi-agent system designed to plan, execute, monitor, and optimize digital marketing campaigns autonomously. Given a natural language campaign brief, CampaignX profiles customers into segments, generates highly personalized A/B email variants, and leverages human-in-the-loop approvals before automatically executing the campaign and running continuous optimization loops based on live performance data.

---

## 🚀 Hackathon Rulebook Compliance & Functional Capabilities

Our solution is specifically architected to meet and exceed every requirement outlined in the **FrostHack | XPECTO 2026 CampaignX Rulebook** (Sections 6 & 10).

### 1. Customer Cohort (Rule 6.1)
The system leverages dynamic API discovery to fetch the live customer cohort required for the active phase (Preliminary or Test) without hardcoded datasets, establishing an accurate master data pool for segmentation.

### 2. Campaign Brief Parsing (Rule 6.2)
CampaignX accepts free-flowing natural language input via the UI. The `brief_parser` agent intelligently extracts the core product (`XDeposit`), key advantages (1% higher returns, 0.25% bonus for female senior citizens), mandatory elements (links), and optimization goals.

### 3. Campaign Planning & Segmentation (Rule 6.3)
The `profiler` agent analyzes the actual cohort schema and instructs the LLM to dynamically create 4 to 9 **mutually exclusive and collectively exhaustive** target segments based on the data. It plans targeted strategies and assigns prime send-hours for each segment.

### 4. Content Generation (Rule 6.4)
The `content_gen` agent autonomously crafts two variants (A/B testing) for each segment. 
- It generates emotional vs. rational **text variations**.
- It decides whether **emojis** are appropriate based on the segment tone.
- It dynamically injects **font variations** (HTML `<b>`, `<i>`, `<u>`).
- It inherently checks and ensures the mandatory **call-to-action URL** (`https://superbfsi.com/xdeposit/explore/`) is correctly placed within the body, as verified by strict output validators.

### 5. Human-in-Loop Approval (Rule 6.5)
The `orchestrator` pauses the pipeline intelligently at the `awaiting_approval` state. The Next.js frontend polls and presents the proposed segments, variants, timelines, and customer lists to the human marketer, who must explicitly approve or safely reject (which triggers content regeneration) before any emails are sent.

### 6. Campaign Scheduling & Execution (Rule 6.6)
**NO Deterministic API Calling!** We built `api_tools.py` which dynamically pulls the live OpenAPI JSON spec, resolves references, and formats the API payload on-the-fly to execute/schedule the campaign precisely as required by the rules.

### 7. Performance Monitoring & Evaluation Metrics (Rule 6.7 & 10.1)
The `analyst` agent autonomously fetches campaign reports via the dynamically discovered API. 
**We implemented the exact Hackathon Evaluation Weightage:** Our system computes a real-time `composite_score` evaluating the performance as `(Click Rate * 0.7) + (Open Rate * 0.3)`.

### 8. Autonomous Optimization (Rule 6.8)
Using the computed composite scores, the `optimizer` agent iteratively re-targets the worst-performing segments in subsequent loops (up to `max_iterations`). It instructs the prompt chain to refine the tone, style, and angle to hunt for higher click and open rates automatically.

### 🏆 Bonus Points Achieved (Rule 10.3)
- [x] **Comprehensive Agent Logging:** Every LLM prompt, reasoning step, and agent output is persistently tracked in the `agent_logs` SQLite table.
- [x] **Real-time Dashboards:** Our Next.js frontend provides an interactive, live-polling dashboard showing the status, current metrics, and variants for ongoing campaigns.

---

## Technical Architecture

The core relies on a **LangGraph-inspired State Machine Pipeline** orchestrated via FastAPI:
1. **brief_parser** ➡️ 2. **profiler** ➡️ 3. **content_gen** ➡️ 
*(Human-in-Loop Pause)* ➡️ 4. **executor** ➡️ 5. **analyst** ➡️ 6. **optimizer** ➡️ *(Loop Back)*

**LLM Fallback Router:** We implemented a robust fail-safe. If the primary LLM (Gemini 2.0 Flash Lite) encounters rate limits or errors, the router automatically falls back to Groq (Llama 3.3 70b), and then Mistral, ensuring 100% uptime for the agent pipeline.

## Tech Stack
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, SQLite, Uvicorn, httpx, jsonref
- **Frontend:** Next.js 14, Tailwind CSS, TypeScript
- **State Management:** Custom Orchestration State Machine with SQLite persistence.

---

## Setup and Installation

1. Copy the environment variables template and add your API keys:
```bash
cp .env.example .env
# Required: GEMINI_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY, CAMPAIGNX_API_KEY, CAMPAIGNX_TEAM_NAME
```

2. Open two terminals and start the application:

**Terminal 1 (Backend - Port 8000):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m backend.db.init_db
python -m uvicorn backend.main:app --reload
```

**Terminal 2 (Frontend - Port 3000):**
```bash
cd frontend
npm install
npm run dev
```

Navigate your browser to [http://localhost:3000](http://localhost:3000).

## Running Tests
Run tests sequentially per sub-phase. (Set `MOCK_API=false` to use live endpoints; requires backend running for Phase 3 tests).

```bash
pytest tests/test_phase1_sub1.py
pytest tests/test_phase1_sub_2_3.py
pytest tests/test_phase2_sub4_to_6.py
pytest tests/test_phase2_sub7.py
pytest tests/test_phase2_sub8.py
pytest tests/test_phase3_parta.py 
```
