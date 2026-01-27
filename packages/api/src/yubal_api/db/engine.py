"""SQLite database engine setup."""

from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine

DB_FILE = "yubal.db"


def create_db_engine(db_path: Path) -> Engine:
    """Create SQLite engine.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy engine configured for SQLite.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )


def init_db(engine: Engine) -> None:
    """Create all tables if they don't exist.

    Args:
        engine: SQLAlchemy engine to use.
    """
    SQLModel.metadata.create_all(engine)
