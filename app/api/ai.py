from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .deps import get_current_user
from ..models.user import User
from ..services.mistral import mistral_completion
from ..models.ai_interaction import AIInteraction
from ..services.database import get_session
from sqlmodel import Session

router = APIRouter(prefix="/ai", tags=["ai"])

class CompletionRequest(BaseModel):
    prompt: str

class CompletionResponse(BaseModel):
    completion: str

@router.post("/completions", response_model=CompletionResponse)
async def create_completion(payload: CompletionRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    completion, model = await mistral_completion(payload.prompt, user_id=current_user.id)
    # Persist user prompt and assistant reply
    session.add(AIInteraction(user_id=current_user.id, model=model, role="user", content=payload.prompt))
    session.add(AIInteraction(user_id=current_user.id, model=model, role="assistant", content=completion))
    session.commit()
    return CompletionResponse(completion=completion)
