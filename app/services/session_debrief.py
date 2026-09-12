"""Session snapshot idempotence and structured debrief validation."""

from datetime import datetime, timezone
import hashlib
import json
from typing import Dict, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..models.coach import CoachSession, CoachSessionAnalysis
from ..schemas.coach import (
    CoachDebrief,
    ExerciseEvaluation,
    ExerciseResult,
    NextAction,
    SessionIn,
)


CONTRACT_VERSION = 1


def build_snapshot(
    session: SessionIn,
    experience_level: Optional[str],
    exercise: Optional[Dict[str, object]],
) -> Dict[str, object]:
    """Build the complete canonical snapshot persisted for an analysis."""
    value = json.loads(session.json(by_alias=True))
    value["experience_level"] = experience_level
    value["exercise"] = exercise
    return value


def content_hash(snapshot: Dict[str, object]) -> str:
    """Hash one canonical snapshot for replay-safe idempotence."""
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upsert_session(
    db: Session,
    user_id: str,
    client_session_id: str,
    snapshot: Dict[str, object],
    snapshot_hash: str,
) -> CoachSession:
    """Create or update the latest server snapshot without prior synchronization."""
    record = db.exec(
        select(CoachSession).where(
            CoachSession.user_id == user_id,
            CoachSession.client_session_id == client_session_id,
        )
    ).first()
    if record is None:
        record = CoachSession(
            user_id=user_id,
            client_session_id=client_session_id,
            content_hash=snapshot_hash,
            snapshot=snapshot,
        )
        db.add(record)
    elif record.content_hash != snapshot_hash:
        record.content_hash = snapshot_hash
        record.snapshot = snapshot
        record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        record = db.exec(
            select(CoachSession).where(
                CoachSession.user_id == user_id,
                CoachSession.client_session_id == client_session_id,
            )
        ).one()
        if record.content_hash != snapshot_hash:
            record.content_hash = snapshot_hash
            record.snapshot = snapshot
            record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(record)
            db.commit()
    db.refresh(record)
    return record


def find_analysis(
    db: Session,
    coach_session_id: str,
    snapshot_hash: str,
    prompt_variant: str,
) -> Optional[CoachSessionAnalysis]:
    """Return an existing analysis for the exact same request inputs."""
    return db.exec(
        select(CoachSessionAnalysis).where(
            CoachSessionAnalysis.coach_session_id == coach_session_id,
            CoachSessionAnalysis.content_hash == snapshot_hash,
            CoachSessionAnalysis.contract_version == CONTRACT_VERSION,
            CoachSessionAnalysis.prompt_variant == prompt_variant,
        )
    ).first()


def persist_analysis(
    db: Session,
    coach_session_id: str,
    snapshot_hash: str,
    prompt_variant: str,
    debrief: CoachDebrief,
    model: str,
) -> CoachSessionAnalysis:
    """Persist one immutable structured analysis separately from its session."""
    record = CoachSessionAnalysis(
        coach_session_id=coach_session_id,
        content_hash=snapshot_hash,
        contract_version=CONTRACT_VERSION,
        prompt_variant=prompt_variant,
        result=json.loads(debrief.json()),
        model=model,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = find_analysis(db, coach_session_id, snapshot_hash, prompt_variant)
        if existing is None:
            raise
        return existing
    db.refresh(record)
    return record


def exercise_result(session: SessionIn) -> Optional[ExerciseResult]:
    """Compute the result only from performed and protocol_followed."""
    if session.exercise_id is None:
        return None
    execution = session.exercise_execution
    if execution is None or execution.performed is None:
        return ExerciseResult.not_evaluable
    if execution.performed is False:
        return ExerciseResult.failed
    if execution.protocol_followed is None:
        return ExerciseResult.not_evaluable
    if execution.protocol_followed.value == "yes":
        return ExerciseResult.succeeded
    return ExerciseResult.failed


def parse_debrief(raw: str, session: SessionIn) -> Tuple[CoachDebrief, bool]:
    """Validate the single model response and provide a safe local fallback."""
    try:
        value = raw.strip()
        if value.startswith("```"):
            lines = value.splitlines()
            value = "\n".join(lines[1:-1])
        parsed = CoachDebrief.parse_obj(json.loads(value))
        used_fallback = False
    except (TypeError, ValueError):
        parsed = _fallback_debrief(session)
        used_fallback = True

    expected_result = exercise_result(session)
    if expected_result is None:
        parsed.exercise_evaluation = None
        if parsed.next_action is NextAction.repeat_exercise:
            parsed.next_action = NextAction.request_progression_coach
    elif parsed.exercise_evaluation is None:
        parsed.exercise_evaluation = ExerciseEvaluation(
            result=expected_result,
            debrief="Résultat établi à partir de la réalisation et du suivi du protocole déclarés.",
        )
    else:
        parsed.exercise_evaluation.result = expected_result
    if session.personal_exercise is not None and parsed.exercise_evaluation is not None:
        scope = "Exercice personnel hors plan de formation."
        if scope.casefold() not in parsed.exercise_evaluation.debrief.casefold():
            remaining = 2000 - len(scope) - 1
            parsed.exercise_evaluation.debrief = (
                f"{scope} {parsed.exercise_evaluation.debrief[:remaining]}"
            )
    return parsed, used_fallback


def _fallback_debrief(session: SessionIn) -> CoachDebrief:
    """Return a factual response when model output cannot be validated."""
    return CoachDebrief(
        debrief=(
            "La session a été enregistrée, mais le débrief détaillé n’a pas pu "
            "être interprété de façon fiable."
        ),
        successes=[
            f"La session contient {len(session.series)} série(s) enregistrée(s)."
        ],
        attention_point=(
            "Relancer le débrief ultérieurement pour obtenir un point d’attention fiable."
        ),
        limitations=["La réponse du modèle ne respectait pas le contrat structuré."],
        next_action=None,
    )
