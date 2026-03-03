# CampaignX — AI Multi-Agent Email Campaign System

**Hackathon:** FrostHack | XPECTO 2026 | InXiteOut | IIT Mandi  
**Team:** Team Aquarium

An AI multi-agent web application for end-to-end email marketing campaign automation for SuperBFSI's XDeposit term deposit product.

## Tech Stack
- **Agent Framework:** Google ADK
- **Backend:** FastAPI + SQLAlchemy
- **Frontend:** Next.js 14 + Tailwind CSS
- **LLMs:** Gemini 2.0 Flash (primary) | Groq (fallback 1) | Mistral (fallback 2)
- **Database:** SQLite (local) / PostgreSQL via Supabase (cloud)

## Setup
1. Copy `.env.example` to `.env` and fill in all API keys
2. Install Python dependencies: `pip install -r requirements.txt`
3. Initialise database: `python -c "from backend.db.session import init_db; init_db()"`
4. Run backend: `uvicorn backend.main:app --reload --port 8000`
5. Run frontend: `cd frontend && npm run dev`
