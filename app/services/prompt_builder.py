"""Construit le prompt d'analyse de session à envoyer à Mistral.

Portage de la logique historiquement présente côté client
(lib/services/coach_analysis_service.dart::buildPrompt) : le client
n'envoie plus le prompt, seulement les données de session ; le
template et l'assemblage vivent désormais côté serveur.
"""
from pathlib import Path
from typing import Dict
import functools

import yaml

from ..schemas.coach import SessionIn

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Mapping prompt_variant -> fichier yaml. Prévu pour la future
# multi-persona (backlog "plusieurs coachs" : neutre / cool).
_VARIANT_FILES: Dict[str, str] = {
    "coach_neutre": "coach_neutre.yaml",
}


class UnknownPromptVariantError(Exception):
    pass


@functools.lru_cache(maxsize=8)
def _load_template(variant: str) -> str:
    filename = _VARIANT_FILES.get(variant)
    if filename is None:
        raise UnknownPromptVariantError(f"prompt_variant inconnu: {variant}")
    path = PROMPTS_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return str(data["prompt"]).strip()


def build_prompt(session: SessionIn, prompt_variant: str = "coach_neutre") -> str:
    template = _load_template(prompt_variant)

    lines = [template, "", "Session :"]
    lines.append(f"Arme : {session.weapon or 'Non renseignée'}")
    lines.append(f"Calibre : {session.caliber or 'Non renseigné'}")
    lines.append(f"Date : {session.date.isoformat() if session.date else 'Non renseignée'}")
    lines.append("Séries :")
    for i, s in enumerate(session.series, start=1):
        lines.append(
            f"- Série {i} : Coups={s.shot_count}, Distance={s.distance}m, "
            f"Points={s.points}, Groupement={s.group_size_cm}cm, Commentaire={s.comment}"
        )
    if session.synthese and session.synthese.strip():
        lines.append("")
        lines.append("Synthèse du tireur :")
        lines.append(session.synthese)

    return "\n".join(lines)
