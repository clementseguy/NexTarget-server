from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SeriesIn(BaseModel):
    shot_count: int = Field(..., ge=1)
    distance: Optional[float] = None
    points: Optional[float] = None
    group_size_cm: Optional[float] = None
    comment: Optional[str] = None


class SessionIn(BaseModel):
    weapon: Optional[str] = None
    caliber: Optional[str] = None
    date: Optional[datetime] = None
    series: List[SeriesIn] = Field(default_factory=list)
    synthese: Optional[str] = None


class AnalyzeSessionRequest(BaseModel):
    session: SessionIn
    prompt_variant: str = "coach_neutre"


class AnalyzeSessionResponse(BaseModel):
    analysis: str
    model: str
    generated_at: datetime
