from datetime import datetime
from sqlmodel import SQLModel, Field
import uuid

class AIInteraction(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id")
    model: str
    role: str  # 'user' or 'assistant'
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
