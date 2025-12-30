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
    import os
    import logging

    logger = logging.getLogger(__name__)

    # Ensure data directory exists and is writable
    data_path = Path(data_dir)
    try:
        data_path.mkdir(parents=True, exist_ok=True)
        # Test write permissions
        test_file = data_path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise PermissionError(f"Cannot write to {data_dir}: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating data directory {data_dir}: {str(e)}")
        raise

    db_path = data_path / "media_janitor.db"
    logger.info(f"Initializing database at: {db_path}")

    # SQLite with check_same_thread=False for FastAPI
    try:
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
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database at {db_path}: {str(e)}")
        raise


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

