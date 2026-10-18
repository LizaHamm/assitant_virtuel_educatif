
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    conversation_id: str = Field(..., min_length=1, max_length=100)


class ChatResponse(BaseModel):
    answer: str

    # US-014 : classification de la question
    category: str | None = None
    category_confidence: float | None = None

    # US-017 : détection de l'intention
    intent: str | None = None
    intent_confidence: float | None = None

    # US-015 : extraction des entités
    entities: dict | None = None

    # US-018 : clarification des questions ambiguës
    clarification_required: bool = False
    clarification_question: str | None = None


class Conversation(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[dict]


class ConversationListResponse(BaseModel):
    conversations: list[Conversation]


class HistoryResponse(BaseModel):
    conversation_id: str
    messages: list[dict]
