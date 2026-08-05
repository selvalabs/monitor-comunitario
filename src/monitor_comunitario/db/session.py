from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from monitor_comunitario.core.config import get_settings

settings = get_settings()


def _connect_args(database_url: str) -> dict[str, object]:
    """Return engine options appropriate for the configured database."""
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    if database_url.startswith(("postgresql", "postgres")):
        return {"prepare_threshold": None}
    return {}


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Create the local SQLite parent folder before SQLAlchemy connects.

    The default development database lives at ./data/monitor_comunitario.db.
    SQLite will create the file, but not the parent folder.
    """
    if not database_url.startswith("sqlite:///"):
        return

    db_path = database_url.replace("sqlite:///", "", 1)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.database_url)

engine: Engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(settings.database_url),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that provides one database session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
