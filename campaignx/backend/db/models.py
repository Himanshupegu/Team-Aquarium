"""
db/models.py
All 6 SQLAlchemy ORM models for CampaignX.
Tables: customer_cohort, campaigns, campaign_reports, agent_logs, api_usage, cohort_meta
"""
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class CustomerCohort(Base):
    """All 18 cohort fields as typed columns. 100% populated — no nulls."""
    __tablename__ = "customer_cohort"

    customer_id         = Column(String, primary_key=True)
    full_name           = Column(String, nullable=False)
    email               = Column(String, nullable=False)
    age                 = Column(Integer, nullable=False)
    gender              = Column(String, nullable=False)        # "Male" / "Female"
    marital_status      = Column(String, nullable=False)        # "Single" / "Married" / "Divorced"
    family_size         = Column(Integer, nullable=False)
    dependent_count     = Column(Integer, nullable=False)
    occupation          = Column(String, nullable=False)
    occupation_type     = Column(String, nullable=False)        # "Salaried" / "Self-Employed"
    monthly_income      = Column(Integer, nullable=False)       # INR
    kyc_status          = Column(String, nullable=False)
    city                = Column(String, nullable=False)
    kids_in_household   = Column(Integer, nullable=False)
    app_installed       = Column(String, nullable=False)        # "Yes" / "No"
    existing_customer   = Column(String, nullable=False)        # "Yes" / "No"
    credit_score        = Column(Integer, nullable=False)
    social_media_active = Column(String, nullable=False)        # "Yes" / "No"
    fetched_at          = Column(DateTime, default=datetime.utcnow)


class Campaign(Base):
    """Every campaign submitted to the CampaignX API."""
    __tablename__ = "campaigns"

    campaign_id     = Column(String, primary_key=True)   # UUID from API
    iteration       = Column(Integer, nullable=False)
    variant_label   = Column(String, nullable=False)     # "A", "B", etc.
    segment_label   = Column(String, nullable=False)     # e.g. "female_seniors"
    subject         = Column(String, nullable=False)
    body            = Column(Text, nullable=False)
    customer_ids    = Column(JSON, nullable=False)        # list of IDs
    send_time       = Column(String, nullable=False)
    strategy_notes  = Column(Text)
    created_at      = Column(DateTime, default=datetime.utcnow)


class CampaignReport(Base):
    """Per-customer EO/EC data from get_report."""
    __tablename__ = "campaign_reports"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id     = Column(String, nullable=False, index=True)  # orchestrator campaign ID
    api_campaign_id = Column(String, nullable=True, index=True)   # API-returned campaign ID
    customer_id     = Column(String, nullable=False)
    email_opened    = Column(String, nullable=False)     # "Y" or "N"
    email_clicked   = Column(String, nullable=False)     # "Y" or "N"
    fetched_at      = Column(DateTime, default=datetime.utcnow)



class AgentLog(Base):
    """Full reasoning trace for every agent decision. Satisfies bonus logging criterion."""
    __tablename__ = "agent_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String, nullable=False)
    agent_name  = Column(String, nullable=False)
    message     = Column(Text, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


class ApiUsageTracker(Base):
    """Track daily API usage to avoid hitting the 100 call limit."""
    __tablename__ = "api_usage"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    date        = Column(String, nullable=False, index=True)   # "YYYY-MM-DD"
    call_count  = Column(Integer, default=0)
    last_updated= Column(DateTime, default=datetime.utcnow)


class CohortMeta(Base):
    """Tracks when the cohort was last fetched — for cache invalidation on 14 March."""
    __tablename__ = "cohort_meta"

    id          = Column(Integer, primary_key=True)
    fetched_date= Column(String, nullable=False)   # "YYYY-MM-DD"
    total_count = Column(Integer, default=0)
    updated_at  = Column(DateTime, default=datetime.utcnow)
