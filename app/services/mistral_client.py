"""Client HTTP pour appeler l'API Mistral depuis le serveur.

Équivalent serveur de l'ancien CoachAnalysisService.fetchAnalysis
côté app (lib/services/coach_analysis_service.dart). La clé API
Mistral ne quitte jamais le serveur.
"""
import httpx

from ..core.config import get_settings


class MistralClientError(Exception):
    """Erreur générique lors de l'appel à Mistral (message user-friendly)."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def fetch_analysis(prompt: str) -> str:
    settings = get_settings()

    if not settings.mistral_api_key:
        raise MistralClientError(
            "Clé API Mistral absente côté serveur (MISTRAL_API_KEY).", status_code=500
        )

    url = f"{settings.mistral_api_base}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=settings.mistral_timeout_seconds) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.mistral_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.mistral_model,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
    except httpx.TimeoutException:
        raise MistralClientError("Le modèle ne répond pas (timeout).", status_code=504)
    except httpx.RequestError as e:
        raise MistralClientError(f"Erreur réseau vers Mistral: {e}", status_code=502)

    if response.status_code == 401:
        raise MistralClientError("Clé API Mistral invalide côté serveur.", status_code=500)
    if response.status_code == 429:
        raise MistralClientError("Trop de requêtes vers Mistral, réessayez plus tard.", status_code=429)
    if response.status_code >= 500:
        raise MistralClientError(f"Erreur serveur Mistral ({response.status_code}).", status_code=502)
    if response.status_code < 200 or response.status_code >= 300:
        raise MistralClientError(f"Erreur HTTP Mistral ({response.status_code}).", status_code=502)

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = None

    if not content or not str(content).strip():
        raise MistralClientError("Réponse vide du modèle.", status_code=502)

    return content
