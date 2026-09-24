from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.chat import ChatRequest, ChatResponse
from app.services.question_service import process_question
from app.services.response_service import generate_response

app = FastAPI(
    title="Assistant Virtuel Éducatif API",
    version="0.1.0",
    description="MVP du chatbot éducatif - US-001",
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


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    question = process_question(request.message)
    answer = generate_response(question)
    return ChatResponse(answer=answer)
