from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import StrictInt, StrictStr, validator
from sqlalchemy import Boolean, CheckConstraint, Column, JSON, true
from sqlmodel import Field, SQLModel


class ExerciseCategory(str, Enum):
    """Categories shared with the Flutter exercise model."""

    precision = "precision"
    group = "group"
    speed = "speed"
    technique = "technique"
    mental = "mental"
    physical = "physical"


class ExerciseType(str, Enum):
    """Locations where an exercise can be performed."""

    stand = "stand"
    home = "home"


class ExerciseDifficulty(str, Enum):
    """Optional experience level associated with an exercise."""

    beginner = "beginner"
    advanced = "advanced"
    expert = "expert"


class ExerciseOrigin(str, Enum):
    """Controlled source of an exercise."""

    personal = "personal"
    coach_catalog = "coach_catalog"


class Exercise(SQLModel):
    """Shared exercise domain model without database persistence."""

    id: StrictStr
    name: StrictStr
    category: ExerciseCategory
    type: ExerciseType
    difficulty: Optional[ExerciseDifficulty] = None
    origin: ExerciseOrigin = ExerciseOrigin.personal
    description: Optional[StrictStr] = None
    duration_minutes: Optional[StrictInt] = Field(None, alias="durationMinutes")
    equipment: Optional[StrictStr] = None
    created_at: datetime = Field(..., alias="createdAt")
    priority: StrictInt = 9999
    goal_ids: List[StrictStr] = Field(default_factory=list, alias="goalIds")
    consignes: List[StrictStr] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True


class CoachCatalogExercise(Exercise, table=True):
    """Persisted exercise prepared for the read-only Coach catalog."""

    __tablename__ = "coach_catalog_exercise"
    __table_args__ = (
        CheckConstraint(
            "origin = 'coach_catalog'",
            name="ck_coach_catalog_exercise_origin",
        ),
    )

    id: StrictStr = Field(primary_key=True)
    origin: ExerciseOrigin = ExerciseOrigin.coach_catalog
    goal_ids: List[StrictStr] = Field(
        default_factory=list,
        alias="goalIds",
        sa_column=Column(JSON, nullable=False),
    )
    consignes: List[StrictStr] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=true()),
    )

    def __init__(self, **data: object) -> None:
        """Build a catalog row while rejecting any non-catalog provenance."""
        origin = data.get("origin", ExerciseOrigin.coach_catalog)
        if ExerciseOrigin(origin) is not ExerciseOrigin.coach_catalog:
            raise ValueError("Coach catalog exercises must use coach_catalog origin")
        super().__init__(**data)

    @validator("origin")
    def validate_catalog_origin(cls, value: ExerciseOrigin) -> ExerciseOrigin:
        """Reject persistence of personal exercises in the Coach catalog."""
        if value is not ExerciseOrigin.coach_catalog:
            raise ValueError("Coach catalog exercises must use coach_catalog origin")
        return value
