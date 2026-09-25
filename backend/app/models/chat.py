from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # Le format UUID est vérifié par Pydantic : toute autre valeur renvoie une erreur 422
    session_id: UUID
    message: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str


class HistoryItem(BaseModel):
    question: str
    answer: str
    created_at: datetime


class HistoryResponse(BaseModel):
    session_id: UUID
    messages: list[HistoryItem]
