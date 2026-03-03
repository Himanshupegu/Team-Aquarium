"""
db/session.py
SQLAlchemy engine, session factory, and database initialization.
Supports SQLite (local) and PostgreSQL (cloud) via DATABASE_URL.
"""
import os
from sqlalchemy import create_engine
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
    """Create all tables defined in models.py."""
    from backend.db.models import Base as ModelsBase  # noqa: F811
    ModelsBase.metadata.create_all(engine)


def get_db():
    """FastAPI dependency — yields a DB session and closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
