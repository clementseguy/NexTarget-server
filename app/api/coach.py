from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..models.user import User
from ..schemas.coach import AnalyzeSessionRequest, AnalyzeSessionResponse
from ..services import mistral_client
from ..services.prompt_builder import build_prompt, UnknownPromptVariantError
from ..services.rate_limiter import coach_rate_limiter
from ..core.config import get_settings
from .deps import get_current_user

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/analyze-session", response_model=AnalyzeSessionResponse)
async def analyze_session(
    payload: AnalyzeSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """Proxifie l'analyse de session vers Mistral.

    Le client n'envoie que les données de session (arme, calibre,
    séries, synthèse) ; ni clé API ni prompt complet ne transitent
    côté client. Endpoint protégé (JWT) : le coach IA est
    "connecté uniquement" (décision produit du 7 juillet 2026).
    """
    if not coach_rate_limiter.allow(current_user.id):
        raise HTTPException(status_code=429, detail="Trop de requêtes, réessayez plus tard.")

    try:
        prompt = build_prompt(payload.session, payload.prompt_variant)
    except UnknownPromptVariantError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        analysis = await mistral_client.fetch_analysis(prompt)
    except mistral_client.MistralClientError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    settings = get_settings()
    return AnalyzeSessionResponse(
        analysis=analysis,
        model=settings.mistral_model,
        generated_at=datetime.now(timezone.utc),
    )
