"""Persisted session snapshots and their separate Coach analyses."""

from datetime import datetime, timezone
from typing import Dict
import uuid

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """Return naive UTC consistently with the existing SQLite models."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CoachSession(SQLModel, table=True):
    """Latest snapshot received for one stable application session."""

    __tablename__ = "coach_session"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "client_session_id", name="uix_coach_session_user_client"
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(index=True)
    client_session_id: str = Field(index=True)
    content_hash: str = Field(index=True)
    snapshot: Dict[str, object] = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class CoachSessionAnalysis(SQLModel, table=True):
    """Immutable structured analysis for one exact session snapshot."""

    __tablename__ = "coach_session_analysis"
    __table_args__ = (
        UniqueConstraint(
            "coach_session_id",
            "content_hash",
            "contract_version",
            "prompt_variant",
            name="uix_coach_analysis_idempotency",
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    coach_session_id: str = Field(index=True, foreign_key="coach_session.id")
    content_hash: str = Field(index=True)
    contract_version: int = Field(default=1)
    prompt_variant: str
    result: Dict[str, object] = Field(sa_column=Column(JSON, nullable=False))
    model: str
    generated_at: datetime = Field(default_factory=_utc_now)
