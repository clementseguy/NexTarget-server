"""Read-only access to active Coach catalog exercises (NT-160)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..models.exercise import CoachCatalogExercise
from ..schemas.exercise import ExerciseSchema
from ..services.database import get_session


router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("/{exercise_id}")
def get_active_exercise(
    exercise_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ExerciseSchema:
    """Return one active Coach catalog exercise by its stable identifier."""
    exercise = session.exec(
        select(CoachCatalogExercise).where(
            CoachCatalogExercise.id == exercise_id,
            CoachCatalogExercise.is_active.is_(True),
        )
    ).first()
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )
    return ExerciseSchema.model_validate(exercise)
