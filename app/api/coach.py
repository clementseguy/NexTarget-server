from datetime import timezone
import json
from typing import Annotated, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.exercise import CoachCatalogExercise, ExerciseOrigin
from ..models.user import User
from ..schemas.coach import AnalyzeSessionRequest, AnalyzeSessionResponse, SessionIn
from ..services import mistral_client
from ..services.database import get_session
from ..services.prompt_builder import build_prompt, UnknownPromptVariantError
from ..services.rate_limiter import coach_rate_limiter
from ..services.session_debrief import (
    build_snapshot,
    content_hash,
    find_analysis,
    parse_debrief,
    persist_analysis,
    upsert_session,
)
from .deps import get_current_user

router = APIRouter(prefix="/coach", tags=["coach"])
logger = get_logger("nextarget.coach")


@router.post(
    "/analyze-session",
    responses={
        422: {"description": "Unknown prompt variant or unavailable exercise"},
        429: {"description": "Coach analysis rate limit exceeded"},
    },
)
async def analyze_session(
    payload: AnalyzeSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> AnalyzeSessionResponse:
    """Persist and debrief one completed session through a single model call.

    Le client n'envoie que les données de session (arme, calibre, exercice
    principal facultatif, séries, synthèse) ; ni clé API ni prompt complet ne transitent
    côté client. Endpoint protégé (JWT) : le coach IA est
    "connecté uniquement" (décision produit du 7 juillet 2026).
    """
    session = payload.session
    logger.debug(
        "coach analysis contract",
        extra={
            "user": {
                "id": current_user.id,
                "experience_level": current_user.experience_level,
            },
            "prompt_variant": payload.prompt_variant,
            "received_session_fields": sorted(
                session.dict(by_alias=True, exclude_unset=True).keys()
            ),
            "session": {
                "has_weapon": bool(session.weapon),
                "has_caliber": bool(session.caliber),
                "date": session.date.isoformat() if session.date else None,
                "has_exercise": session.exercise_id is not None,
                "series_count": len(session.series),
                "series": [
                    {
                        "shot_count": series.shot_count,
                        "distance": series.distance,
                        "points": series.points,
                        "group_size_cm": series.group_size_cm,
                        "has_comment": bool(series.comment),
                    }
                    for series in session.series
                ],
                "has_synthese": bool(session.synthese),
                "has_personal_exercise": session.personal_exercise is not None,
                "has_exercise_execution": session.exercise_execution is not None,
            },
        },
    )

    try:
        exercise = _resolve_exercise(db, session)
        prompt = build_prompt(
            session,
            payload.prompt_variant,
            payload.experience_level.value if payload.experience_level else None,
            exercise,
        )
    except UnknownPromptVariantError as e:
        raise HTTPException(status_code=422, detail=str(e))

    snapshot = build_snapshot(
        session,
        payload.experience_level.value if payload.experience_level else None,
        exercise,
    )
    snapshot_hash = content_hash(snapshot)
    persisted_session = upsert_session(
        db,
        current_user.id,
        str(session.session_id),
        snapshot,
        snapshot_hash,
    )
    existing = find_analysis(
        db, persisted_session.id, snapshot_hash, payload.prompt_variant
    )
    if existing is not None:
        return _response(existing, session.session_id, reused=True)

    if not coach_rate_limiter.allow(current_user.id):
        raise HTTPException(
            status_code=429, detail="Trop de requêtes, réessayez plus tard."
        )

    try:
        raw_analysis = await mistral_client.fetch_analysis(prompt)
    except mistral_client.MistralClientError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    settings = get_settings()
    debrief, used_fallback = parse_debrief(raw_analysis, session)
    if used_fallback:
        logger.warning(
            "invalid structured coach response",
            extra={"client_session_id": str(session.session_id)},
        )
    analysis = persist_analysis(
        db,
        persisted_session.id,
        snapshot_hash,
        payload.prompt_variant,
        debrief,
        settings.mistral_model,
    )
    return _response(analysis, session.session_id, reused=False)


def _resolve_exercise(db: Session, session: SessionIn) -> Optional[Dict[str, object]]:
    """Resolve catalog content server-side or validate the personal snapshot."""
    if session.exercise_id is None:
        return None
    if session.exercise_origin is ExerciseOrigin.personal:
        return json.loads(session.personal_exercise.json())
    exercise = db.exec(
        select(CoachCatalogExercise).where(
            CoachCatalogExercise.id == session.exercise_id,
            CoachCatalogExercise.is_active.is_(True),
        )
    ).first()
    if exercise is None:
        raise HTTPException(status_code=422, detail="Exercise not available")
    return json.loads(exercise.json(by_alias=True))


def _response(record, client_session_id, reused: bool) -> AnalyzeSessionResponse:
    """Map one persisted analysis to the public response contract."""
    generated_at = record.generated_at
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return AnalyzeSessionResponse(
        **record.result,
        analysis_id=record.id,
        session_id=client_session_id,
        model=record.model,
        generated_at=generated_at,
        reused=reused,
    )
