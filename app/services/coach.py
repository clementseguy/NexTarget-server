"""Coaching orchestrator service (v1 minimal).

Pipeline:
1. Build structured prompt from goal + optional context
2. Call Mistral via existing mistral_completion (user perspective) but request a list format
3. Parse resulting text into individual advices
4. Score advices (trivial heuristic: length inverse penalty)
"""
from __future__ import annotations
from typing import List, Dict
import re

from .mistral import mistral_completion
from typing import Optional

PROMPT_TEMPLATE = """Tu es un coach pragmatique.
Objectif utilisateur: {goal}
Contexte additionnel (optionnel): {context}

Donne une liste de 5 à 8 conseils actionnables, concis (max 18 mots), classés naturellement.
Format strict:
1. Conseil...
2. Conseil...
3. ...
""".strip()

def build_prompt(goal: str, context: Optional[str]) -> str:
    ctx = context.strip() if context else "(aucun)"
    return PROMPT_TEMPLATE.format(goal=goal.strip(), context=ctx)

async def generate_advices(goal: str, context: Optional[str], user_id: str):
    prompt = build_prompt(goal, context)
    completion, model = await mistral_completion(prompt, user_id=user_id)
    advices = parse_advices(completion)
    scored = score_advices(advices)
    return {
        "model": model,
        "raw": completion,
        "advices": scored,
        "used_prompt": prompt,
    }

ADVICE_LINE_RE = re.compile(r"^(?:\d+\.|[-*])\s*(.+)$")

def parse_advices(text: str) -> List[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    results: List[str] = []
    for line in lines:
        m = ADVICE_LINE_RE.match(line)
        if m:
            advice = m.group(1).strip()
            # remove trailing period duplication
            results.append(advice)
    # fallback: if parsing failed entirely, return first 5 non-empty sentences
    if not results:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        results = [s.strip() for s in sentences if s.strip()][:5]
    # de-duplicate preserving order
    seen = set()
    uniq = []
    for a in results:
        if a.lower() not in seen:
            seen.add(a.lower())
            uniq.append(a)
    return uniq

def score_advices(advices: List[str]) -> List[Dict[str, float | str]]:
    scored = []
    for idx, advice in enumerate(advices):
        length = len(advice)
        # simple scoring: base on position and brevity
        score = max(0.0, 1.0 - (length / 160.0)) + (0.05 * (len(advices) - idx))
        scored.append({"text": advice, "score": round(score, 4)})
    return scored
