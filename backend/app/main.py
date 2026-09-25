from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models.chat import ChatRequest, ChatResponse, HistoryItem, HistoryResponse
from app.services.history_service import get_history, save_exchange
from app.services.question_service import process_question
from app.services.response_service import generate_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # crée les tables au démarrage si besoin
    yield


app = FastAPI(
    title="Assistant Virtuel Éducatif API",
    version="0.2.0",
    description="MVP du chatbot éducatif - US-001 et US-002",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        question = process_question(request.message)
    except ValueError as error:
        # Cas d'un message composé uniquement d'espaces
        raise HTTPException(status_code=400, detail=str(error))

    answer = generate_response(question)
    save_exchange(db, request.session_id, question, answer)
    return ChatResponse(answer=answer)


@app.get("/api/history/{session_id}", response_model=HistoryResponse)
def history(session_id: UUID, db: Session = Depends(get_db)):
    """Historique d'une session. Il n'existe volontairement aucune route
    pour lister toutes les sessions : on ne lit que celle dont on connaît l'UUID."""
    exchanges = get_history(db, session_id)
    return HistoryResponse(
        session_id=session_id,
        messages=[
            HistoryItem(question=e.question, answer=e.answer, created_at=e.created_at)
            for e in exchanges
        ],
    )
