from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    conversation_id: str = Field(..., min_length=1, max_length=100)


class ChatResponse(BaseModel):
    answer: str


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