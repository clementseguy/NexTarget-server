from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from typing import Optional, List

from .deps import get_current_user
from ..models.user import User
from ..models.ai_interaction import AIInteraction
from ..services.coach import generate_advices
from ..services.database import get_session

router = APIRouter(prefix="/coach", tags=["coach"])

class AdviceRequest(BaseModel):
    goal: str
    context: Optional[str] = None
    top_n: Optional[int] = None

class AdviceItem(BaseModel):
    text: str
    score: float

class AdviceResponse(BaseModel):
    advices: List[AdviceItem]
    model: str

@router.post("/advice", response_model=AdviceResponse)
async def advice(payload: AdviceRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    result = await generate_advices(goal=payload.goal, context=payload.context, user_id=current_user.id)
    advices = result["advices"]
    if payload.top_n:
        advices = advices[: payload.top_n]

    # Persist interactions (prompt + combined?)
    session.add(AIInteraction(user_id=current_user.id, model=result["model"], role="user", content=result["used_prompt"]))
    session.add(AIInteraction(user_id=current_user.id, model=result["model"], role="assistant", content=result["raw"]))
    session.commit()

    return AdviceResponse(advices=[AdviceItem(**a) for a in advices], model=result["model"])
