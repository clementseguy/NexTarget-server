import time
import httpx
from fastapi import HTTPException
from typing import Tuple

from ..core.config import get_settings

settings = get_settings()

# Simple in-memory rate limiting structure (user_id -> [timestamps])
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30  # naive placeholder
_rate_buckets: dict[str, list[float]] = {}

def _rate_limit_check(user_id: str):
    now = time.time()
    bucket = _rate_buckets.setdefault(user_id, [])
    # purge old
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)

async def mistral_completion(prompt: str, user_id: str) -> Tuple[str, str]:
    if not settings.mistral_api_key:
        raise HTTPException(status_code=500, detail="Mistral API key not configured")
    if len(prompt) > 4000:
        raise HTTPException(status_code=400, detail="Prompt too long")

    _rate_limit_check(user_id)

    headers = {
        "Authorization": f"Bearer {settings.mistral_api_key}",
        "Content-Type": "application/json",
    }
    model = settings.mistral_model
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 512,
        "stream": False,
    }

    timeout = httpx.Timeout(settings.mistral_timeout_seconds)
    start = time.perf_counter()
    async with httpx.AsyncClient(base_url=settings.mistral_api_base, headers=headers, timeout=timeout) as client:
        try:
            resp = await client.post("/chat/completions", json=data)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Mistral upstream error: {e}")
    latency_ms = (time.perf_counter() - start) * 1000
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Mistral error: {resp.text}")
    payload = resp.json()
    try:
        completion = payload["choices"][0]["message"]["content"].strip()
    except Exception:
        raise HTTPException(status_code=502, detail="Unexpected Mistral response structure")

    # (Optionnel) on pourrait logguer ici; pour l'instant simple print dev
    if settings.debug:
        print(f"[Mistral] model={model} latency={latency_ms:.1f}ms prompt_len={len(prompt)}")
    return completion, model
