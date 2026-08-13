from uuid import UUID
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )
    conversation_id: UUID | None = None
    

class ChatResponse(BaseModel):
    answer: str