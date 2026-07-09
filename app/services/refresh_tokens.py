"""Refresh token issuance, rotation and revocation (NT-048).

Security model:
- Raw tokens are high-entropy random strings, returned once to the client;
  only their SHA-256 hash is persisted.
- Rotation: consuming a refresh token revokes it and issues a new one in
  the same *family*.
- Reuse detection: presenting an already-revoked token is treated as a
  compromise signal — the whole family is revoked (the legitimate holder
  will simply re-login).
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import uuid

from sqlmodel import Session, select

from ..core.config import get_settings
from ..models.refresh_token import RefreshToken


class RefreshTokenError(Exception):
    """Invalid, expired, revoked or reused refresh token."""


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.utcnow()


def issue_refresh_token(
    session: Session,
    user_id: str,
    family_id: Optional[str] = None,
) -> Tuple[str, RefreshToken]:
    """Create and persist a new refresh token.

    Returns:
        Tuple (raw_token, record). The raw token is never stored.
    """
    settings = get_settings()
    raw = secrets.token_urlsafe(48)
    record = RefreshToken(
        user_id=user_id,
        token_hash=_hash(raw),
        family_id=family_id or str(uuid.uuid4()),
        expires_at=_now() + timedelta(days=settings.refresh_token_exp_days),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return raw, record


def _get_by_raw(session: Session, raw_token: str) -> Optional[RefreshToken]:
    return session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == _hash(raw_token))
    ).first()


def revoke_family(session: Session, family_id: str) -> None:
    """Revoke every active token of a rotation family."""
    tokens = session.exec(
        select(RefreshToken).where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at == None,  # noqa: E711 (SQL expression)
        )
    ).all()
    now = _now()
    for t in tokens:
        t.revoked_at = now
        session.add(t)
    session.commit()


def rotate_refresh_token(session: Session, raw_token: str) -> Tuple[str, RefreshToken]:
    """Consume a refresh token and issue its successor (same family).

    Raises:
        RefreshTokenError: unknown, expired, revoked (reuse ⇒ family revoked).
    """
    record = _get_by_raw(session, raw_token)
    if record is None:
        raise RefreshTokenError("Invalid refresh token")

    if record.revoked_at is not None:
        # Reuse of a rotated/revoked token: compromise signal.
        revoke_family(session, record.family_id)
        raise RefreshTokenError("Refresh token reuse detected")

    if record.expires_at <= _now():
        raise RefreshTokenError("Refresh token expired")

    record.revoked_at = _now()
    session.add(record)
    session.commit()

    return issue_refresh_token(session, record.user_id, family_id=record.family_id)


def revoke_refresh_token(session: Session, raw_token: str) -> None:
    """Revoke the token's whole family (logout). No-op if unknown."""
    record = _get_by_raw(session, raw_token)
    if record is not None:
        revoke_family(session, record.family_id)
