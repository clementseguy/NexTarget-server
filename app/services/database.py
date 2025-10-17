from sqlmodel import SQLModel, create_engine, Session
from ..core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, echo=settings.debug, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})

# Ensure models imported so metadata includes all tables
from ..models.user import User  # noqa: F401

def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
