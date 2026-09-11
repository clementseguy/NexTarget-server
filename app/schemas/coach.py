from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

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


class ExperienceLevel(str, Enum):
    """Experience level already stored in the user profile."""

    beginner = "beginner"
    advanced = "advanced"
    expert = "expert"


class HandMethod(str, Enum):
    """Supported firearm grips for one series."""

    one = "one"
    two = "two"


class ExerciseResult(str, Enum):
    """Closed result computed from the user's execution declaration."""

    succeeded = "succeeded"
    failed = "failed"
    not_evaluable = "not_evaluable"


class NextAction(str, Enum):
    """Only follow-up actions allowed to the session Coach."""

    repeat_exercise = "repeat_exercise"
    request_progression_coach = "request_progression_coach"


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
    id: Optional[conint(strict=True, ge=0)] = None
    shot_count: conint(strict=True, ge=1, le=1000)
    distance: Optional[float] = None
    points: Optional[float] = None
    group_size_cm: Optional[float] = None
    comment: Optional[SeriesComment] = None
    hand_method: HandMethod = HandMethod.two
    completed: StrictBool = True
    draft_started: StrictBool = True
    score_entered: StrictBool = True

    class Config:
        extra = "forbid"


class SessionIn(BaseModel):
    session_id: UUID
    session_type: Literal["detailed"] = "detailed"
    status: Literal["réalisée"] = "réalisée"
    weapon: Optional[ShortUserText] = None
    caliber: Optional[ShortUserText] = None
    date: Optional[datetime] = None
    category: Optional[ShortUserText] = None
    exercise_id: Optional[ExerciseId] = Field(None, alias="exerciseId")
    exercise_origin: Optional[ExerciseOrigin] = None
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
        origin = values.get("exercise_origin")
        if snapshot is not None and snapshot.id != exercise_id:
            raise ValueError("Personal exercise snapshot id must match exerciseId")
        if exercise_id is None and any(
            value is not None for value in (origin, snapshot, execution)
        ):
            raise ValueError("Exercise details require exerciseId")
        if exercise_id is not None and origin is None:
            raise ValueError("exercise_origin is required with exerciseId")
        if origin is ExerciseOrigin.personal and snapshot is None:
            raise ValueError("Personal exercise requires a bounded snapshot")
        if origin is ExerciseOrigin.coach_catalog and snapshot is not None:
            raise ValueError("Catalog exercise must be resolved by the server")
        return values

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"


class AnalyzeSessionRequest(BaseModel):
    session: SessionIn
    experience_level: Optional[ExperienceLevel] = None
    prompt_variant: constr(strict=True, min_length=1, max_length=32) = "coach_neutre"

    class Config:
        extra = "forbid"


class ExerciseEvaluation(BaseModel):
    """Structured exercise-specific part of a debrief."""

    result: ExerciseResult
    debrief: constr(strict=True, strip_whitespace=True, min_length=1, max_length=2000)

    class Config:
        extra = "forbid"


class CoachDebrief(BaseModel):
    """Validated decision returned by the session Coach."""

    debrief: constr(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
    successes: conlist(
        constr(strict=True, strip_whitespace=True, min_length=1, max_length=1000),
        min_items=1,
        max_items=3,
    )
    attention_point: constr(
        strict=True, strip_whitespace=True, min_length=1, max_length=2000
    )
    limitations: conlist(
        constr(strict=True, strip_whitespace=True, min_length=1, max_length=1000),
        max_items=5,
    ) = Field(default_factory=list)
    exercise_evaluation: Optional[ExerciseEvaluation] = None
    next_action: Optional[NextAction] = None

    class Config:
        extra = "forbid"


class AnalyzeSessionResponse(CoachDebrief):
    """Public response enriched with persistence and generation metadata."""

    analysis_id: UUID
    session_id: UUID
    model: str
    generated_at: datetime
    reused: bool = False
