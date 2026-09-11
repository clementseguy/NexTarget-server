from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.user import User
from ..schemas.coach import AnalyzeSessionRequest, AnalyzeSessionResponse
from ..services import mistral_client
from ..services.prompt_builder import build_prompt, UnknownPromptVariantError
from ..services.rate_limiter import coach_rate_limiter
from .deps import get_current_user

router = APIRouter(prefix="/coach", tags=["coach"])
logger = get_logger("nextarget.coach")


@router.post("/analyze-session", response_model=AnalyzeSessionResponse)
async def analyze_session(
    payload: AnalyzeSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """Proxifie l'analyse de session vers Mistral.

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

    if not coach_rate_limiter.allow(current_user.id):
        raise HTTPException(
            status_code=429, detail="Trop de requêtes, réessayez plus tard."
        )

    try:
        prompt = build_prompt(payload.session, payload.prompt_variant)
    except UnknownPromptVariantError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        analysis = await mistral_client.fetch_analysis(prompt)
    except mistral_client.MistralClientError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    if session.personal_exercise is not None:
        analysis = f"Exercice personnel hors plan de formation.\n\n{analysis}"

    settings = get_settings()
    return AnalyzeSessionResponse(
        analysis=analysis,
        model=settings.mistral_model,
        generated_at=datetime.now(timezone.utc),
    )
