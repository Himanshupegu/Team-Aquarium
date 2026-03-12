"""
db/session.py
SQLAlchemy engine, session factory, and database initialization.
Supports SQLite (local) and PostgreSQL (cloud) via DATABASE_URL.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./campaignx.db")

# PostgreSQL connection pooling config (ignored for SQLite automatically)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,     # reconnects if cloud DB connection drops
    pool_recycle=300,       # recycle connections every 5 min for cloud
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def init_db():
    """Create all tables defined in models.py and handle migrations."""
    from backend.db.models import Base as ModelsBase
    ModelsBase.metadata.create_all(engine)

    # Temporary Migration Fixes
    try:
        with engine.begin() as conn:
            # Check if iteration column exists in campaign_reports
            query_reports = text("PRAGMA table_info(campaign_reports);")
            res_reports = conn.execute(query_reports)
            columns_reports = [row[1] for row in res_reports]
            if "iteration" not in columns_reports:
                print("[db/session] Migrating: Adding 'iteration' column to campaign_reports")
                conn.execute(text("ALTER TABLE campaign_reports ADD COLUMN iteration INTEGER;"))

            # Check if segments column exists in campaigns
            query_camps = text("PRAGMA table_info(campaigns);")
            res_camps = conn.execute(query_camps)
            columns_camps = [row[1] for row in res_camps]
            if "segments" not in columns_camps:
                print("[db/session] Migrating: Adding 'segments' column to campaigns")
            # Check if all_results column exists in campaigns
            query_results = text("PRAGMA table_info(campaigns);")
            res_results = conn.execute(query_results)
            columns_results = [row[1] for row in res_results]
            if "all_results" not in columns_results:
                print("[db/session] Migrating: Adding 'all_results' column to campaigns")
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN all_results JSON;"))
    except Exception as e:
        print(f"[db/session] Migration skipped or failed: {e}")


def get_db():
    """FastAPI dependency — yields a DB session and closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
