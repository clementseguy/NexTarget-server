"""Rate limiting minimal en mémoire pour les endpoints qui coûtent de
l'argent (appels Mistral). Volontairement simple (usage perso /
petite échelle) : fenêtre glissante par utilisateur, stockée en
mémoire process. À remplacer par Redis si multi-instance un jour
(cf. SECURITY_ANALYSIS.md, même limite déjà connue pour l'OAuth state).
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True


# 10 analyses / 5 minutes par utilisateur : large pour un usage perso,
# suffisant pour éviter un abus qui viderait le quota Mistral.
coach_rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=300)
