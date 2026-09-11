from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import StrictInt, StrictStr
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
