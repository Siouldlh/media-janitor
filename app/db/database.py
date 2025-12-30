"""SQLite database setup and connection."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pathlib import Path
from typing import Generator

from app.config import get_config

# Global engine and session factory
engine = None
SessionLocal = None


def init_db(data_dir: str = "/data") -> None:
    """Initialize database connection."""
    global engine, SessionLocal

    db_path = Path(data_dir) / "media_janitor.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # SQLite with check_same_thread=False for FastAPI
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    from app.db.models import Base
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_sync() -> Session:
    """Get database session (synchronous, for non-async contexts)."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return SessionLocal()

