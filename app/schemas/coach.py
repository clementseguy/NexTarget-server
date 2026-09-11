from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    StrictBool,
    conint,
    conlist,
    constr,
    root_validator,
    validator,
)

from ..models.exercise import ExerciseOrigin


ExerciseId = constr(strict=True, strip_whitespace=True, min_length=1, max_length=128)
ShortUserText = constr(strict=True, max_length=120)
SeriesComment = constr(strict=True, max_length=1000)
SessionSummary = constr(strict=True, max_length=2000)
ExerciseDescription = constr(strict=True, max_length=2000)
ExerciseInstruction = constr(strict=True, min_length=1, max_length=500)
ExecutionComment = constr(strict=True, max_length=1000)


class ProtocolFollowed(str, Enum):
    """Controlled declaration of how closely the exercise protocol was followed."""

    yes = "yes"
    partially = "partially"
    no = "no"


class PersonalExerciseSnapshotIn(BaseModel):
    """Bounded, transient subset needed to understand a personal exercise."""

    id: ExerciseId
    name: constr(strict=True, strip_whitespace=True, min_length=1, max_length=120)
    origin: ExerciseOrigin
    description: Optional[ExerciseDescription] = None
    consignes: conlist(ExerciseInstruction, max_items=20) = Field(default_factory=list)

    @validator("origin")
    def require_personal_origin(cls, value: ExerciseOrigin) -> ExerciseOrigin:
        """Prevent catalog content from entering through the personal snapshot."""
        if value is not ExerciseOrigin.personal:
            raise ValueError("Personal exercise snapshot must use personal origin")
        return value

    class Config:
        extra = "forbid"


class ExerciseExecutionIn(BaseModel):
    """User-declared execution facts used by the initial exercise debrief."""

    performed: Optional[StrictBool] = None
    protocol_followed: Optional[ProtocolFollowed] = None
    comment: Optional[ExecutionComment] = None

    class Config:
        extra = "forbid"


class SeriesIn(BaseModel):
    shot_count: conint(strict=True, ge=1, le=1000)
    distance: Optional[float] = None
    points: Optional[float] = None
    group_size_cm: Optional[float] = None
    comment: Optional[SeriesComment] = None

    class Config:
        extra = "forbid"


class SessionIn(BaseModel):
    weapon: Optional[ShortUserText] = None
    caliber: Optional[ShortUserText] = None
    date: Optional[datetime] = None
    exercise_id: Optional[ExerciseId] = Field(None, alias="exerciseId")
    series: conlist(SeriesIn, max_items=100) = Field(default_factory=list)
    synthese: Optional[SessionSummary] = None
    personal_exercise: Optional[PersonalExerciseSnapshotIn] = None
    exercise_execution: Optional[ExerciseExecutionIn] = None

    @root_validator
    def validate_personal_exercise_context(cls, values):
        """Keep the transient snapshot tied to the analyzed session only."""
        snapshot = values.get("personal_exercise")
        execution = values.get("exercise_execution")
        exercise_id = values.get("exercise_id")
        if snapshot is not None and snapshot.id != exercise_id:
            raise ValueError("Personal exercise snapshot id must match exerciseId")
        if execution is not None and snapshot is None:
            raise ValueError("Exercise execution requires a personal exercise snapshot")
        return values

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"


class AnalyzeSessionRequest(BaseModel):
    session: SessionIn
    prompt_variant: constr(strict=True, min_length=1, max_length=32) = "coach_neutre"

    class Config:
        extra = "forbid"


class AnalyzeSessionResponse(BaseModel):
    analysis: str
    model: str
    generated_at: datetime
