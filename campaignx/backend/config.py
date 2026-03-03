import os
from dotenv import load_dotenv

load_dotenv()

# ── CampaignX API ─────────────────────────────────────────────────────────
CAMPAIGNX_API_KEY   = os.getenv("CAMPAIGNX_API_KEY", "")
CAMPAIGNX_BASE_URL  = os.getenv("CAMPAIGNX_BASE_URL", "https://campaignx.inxiteout.ai")
OPENAPI_SPEC_URL    = f"{CAMPAIGNX_BASE_URL}/openapi.json"
CAMPAIGN_CTA_URL    = "https://superbfsi.com/xdeposit/explore/"

# ── LLMs ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
MISTRAL_API_KEY     = os.getenv("MISTRAL_API_KEY", "")

GEMINI_MODEL        = "gemini-2.0-flash-lite"
GROQ_MODEL          = "llama-3.3-70b-versatile"
MISTRAL_MODEL       = "mistral-small-latest"

# ── Database ───────────────────────────────────────────────────────────────
DATABASE_URL        = os.getenv("DATABASE_URL", "sqlite:///./campaignx.db")

# ── Server ────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS     = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
PORT                = int(os.getenv("PORT", "8000"))

# ── Business Rules (from hackathon spec) ──────────────────────────────────
TEST_PHASE_START    = "2026-03-14"   # Cohort resets at midnight this date
MAX_BODY_CHARS      = 5000
MAX_SUBJECT_CHARS   = 200
METRO_CITIES        = {
    "mumbai", "delhi", "bengaluru", "bangalore",
    "hyderabad", "chennai", "kolkata", "pune", "ahmedabad"
}
