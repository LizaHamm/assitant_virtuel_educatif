from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    Conversation,
    ConversationListResponse,
    HistoryResponse,
)

from app.services.question_service import process_question
from app.services.response_service import generate_response

from app.services.history_service import (
    create_conversation,
    get_conversations,
    get_conversation,
    add_message,
    get_history,
)


app = FastAPI(
    title="Assistant Virtuel Éducatif API",
    version="0.3.0",
    description="Assistant Virtuel Éducatif - gestion des conversations",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------
# CONVERSATIONS
# ---------------------------------------------------------


@app.post("/api/conversations", response_model=Conversation)
def new_conversation():
    """Crée une nouvelle conversation."""

    return create_conversation()


@app.get(
    "/api/conversations",
    response_model=ConversationListResponse,
)
def list_conversations():
    """Retourne toutes les conversations."""

    return ConversationListResponse(
        conversations=get_conversations()
    )


@app.get(
    "/api/conversations/{conversation_id}",
    response_model=Conversation,
)
def get_one_conversation(conversation_id: str):
    """Retourne une conversation complète."""

    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation introuvable.",
        )

    return conversation


# ---------------------------------------------------------
# CHAT
# ---------------------------------------------------------


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Envoie une question dans une conversation existante."""

    conversation = get_conversation(request.conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation introuvable.",
        )

    question = process_question(request.message)

    answer = generate_response(question)

    # Stockage de la question
    add_message(
        conversation_id=request.conversation_id,
        sender="user",
        text=question,
    )

    # Stockage de la réponse
    add_message(
        conversation_id=request.conversation_id,
        sender="bot",
        text=answer,
    )

    return ChatResponse(answer=answer)


# ---------------------------------------------------------
# HISTORIQUE D'UNE CONVERSATION
# ---------------------------------------------------------


@app.get(
    "/api/history/{conversation_id}",
    response_model=HistoryResponse,
)
def history(conversation_id: str):
    """Retourne l'historique d'une conversation."""

    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation introuvable.",
        )

    return HistoryResponse(
        conversation_id=conversation_id,
        messages=get_history(conversation_id),
    )