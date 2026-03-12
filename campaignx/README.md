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

## 🚀 Core Features & Capabilities

CampaignX provides an end-to-end automated marketing workflow. Here are its key functional capabilities:

### 1. Dynamic Customer Cohort Integration
The system leverages dynamic API discovery to fetch live customer cohorts on demand. It does not rely on hardcoded datasets, establishing an accurate, up-to-date master data pool for customer segmentation.

### 2. Natural Language Brief Parsing
CampaignX accepts free-flowing natural language marketing briefs via the UI. The `brief_parser` agent intelligently extracts the core product (e.g., `XDeposit`), key advantages (e.g., higher returns, bonuses for specific demographics), mandatory elements (links), and optimization goals.

### 3. Campaign Planning & Intelligent Segmentation
The `profiler` agent analyzes the actual cohort schema and instructs the LLM to dynamically create 4 to 9 **mutually exclusive and collectively exhaustive** target segments based on the data. It formulates targeted strategies and assigns prime send-hours tailored to each segment's profile.

### 4. Automated Content Generation
The `content_gen` agent autonomously crafts two distinct email variants (A/B testing) for each segment:
- Generates **emotional vs. rational** text variations based on the segment's strategy.
- Selects and inserts appropriate **emojis** to match the segment tone.
- Dynamically injects **font formatting** (HTML `<b>`, `<i>`, `<u>`) for emphasis.
- Uses strict output validators to ensure mandatory **call-to-action URLs** are correctly placed within every email body.

### 5. Human-in-Loop Approval Gate
While fully automated, CampaignX incorporates a critical human safety valve. The `orchestrator` pauses the pipeline at the `awaiting_approval` state. The Next.js frontend polls and presents the proposed segments, email variants, timelines, and customer lists to the human marketer. The marketer must explicitly approve or reject (which triggers smart content regeneration based on their feedback) before any campaigns are dispatched.

### 6. Dynamic Campaign Execution 
The system avoids deterministic API calling. Instead, the `api_tools.py` module dynamically discovers and pulls the live OpenAPI JSON spec, resolves references, and formats the API payloads on-the-fly to execute and schedule campaigns.

### 7. Real-Time Performance Analytics
The `analyst` agent autonomously fetches campaign reports via the dynamically discovered APIs immediately after execution. It computes a real-time `composite_score` evaluating the overall performance. By default, the optimization targets prioritize clicks over opens (calculated as `(Click Rate * 0.7) + (Open Rate * 0.3)`).

### 8. Autonomous Optimization Loop
Using the computed composite scores, the `optimizer` agent iteratively re-targets the worst-performing segments in subsequent loops (up to a defined `max_iterations` limit). It instructs the prompt chain to automatically refine the tone, style, and advertising angle to iteratively hunt for higher click and open rates.

### ✨ Extended Capabilities
- **Comprehensive Agent Logging:** Every LLM prompt, logical reasoning step, and agent output is persistently tracked in the `agent_logs` SQLite table, providing full observability into the AI's decision-making process.
- **Real-Time Dashboards:** The Next.js frontend provides an interactive, live-polling dashboard showing the status, current metrics, and active variants for ongoing campaigns.

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
