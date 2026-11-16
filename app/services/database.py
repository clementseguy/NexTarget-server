from sqlmodel import SQLModel, create_engine, Session
from ..core.config import get_settings
from ..core.logging import get_logger

settings = get_settings()
logger = get_logger("nextarget.database")


def _normalize_database_url(url: str) -> str:
    """Make the SQL driver explicit (NT-071).

    Neon (and some tooling) hand out bare ``postgres://``/``postgresql://``
    URLs. SQLAlchemy 2.x rejects the legacy ``postgres://`` scheme outright,
    and an undeclared driver on ``postgresql://`` silently picks whichever
    DBAPI happens to be importable. Pin it to psycopg2 so the driver is
    explicit and reproducible across environments.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


_database_url = _normalize_database_url(settings.database_url)
_is_sqlite = _database_url.startswith("sqlite")

engine = create_engine(
    _database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # Neon (serverless Postgres) can close idle connections; pre_ping avoids
    # surfacing stale-connection errors on the first request after a lull.
    pool_pre_ping=not _is_sqlite,
)

# Ensure models imported so metadata includes all tables
from ..models.user import User  # noqa: E402,F401
from ..models.refresh_token import RefreshToken  # noqa: E402,F401
from ..models.exercise import CoachCatalogExercise  # noqa: E402,F401
from ..models.coach import CoachSession, CoachSessionAnalysis  # noqa: E402,F401


def init_db() -> None:
    """Create tables for local/dev SQLite only.

    In production (PostgreSQL), Alembic is the sole source of truth for the
    schema (NT-071, see `alembic/`) — migrations run before Uvicorn starts
    (`scripts/run_migrations.py`). Calling ``create_all()`` there would let
    SQLModel silently drift from the migration history, so it is a
    deliberate no-op outside SQLite.
    """
    if _is_sqlite:
        SQLModel.metadata.create_all(engine)
    else:
        logger.info("init_db skipped: non-SQLite database, schema owned by Alembic")


def get_session():
    with Session(engine) as session:
        yield session
