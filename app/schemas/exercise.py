from typing import Any, Dict

from pydantic import BaseModel

from ..models.exercise import Exercise


class ExerciseSchema(Exercise):
    """JSON contract for the shared exercise model."""

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        """Serialize without SQLModel's deprecated Pydantic v1 shim."""
        return BaseModel.dict(self, **kwargs)
