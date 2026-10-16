
import os
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    Conversation,
    ConversationListResponse,
    HistoryResponse,
)
from app.services.question_service import process_question
from app.services.bilingual_service import generate_response, translate_text
from app.services.history_service import (
    create_conversation,
    get_conversations,
    get_conversation,
    add_message,
    get_history,
)
from app.services.log_service import (
    init_log_database,
    log_question,
    log_security_event,
    get_connection,
)
from app.services.security_service import check_message_security
from app.services.rate_limit_service import check_rate_limit

from app.kiosk import router as kiosk_router
from app.notifications import router as notifications_router
from app.proactive import router as proactive_router
from app.sso import router as sso_router

from collections import Counter
from datetime import timedelta 


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Assistant Virtuel Éducatif API",
    version="1.1.0",
    description="Assistant Virtuel Éducatif - ESIC",
)

app.include_router(kiosk_router)
app.include_router(notifications_router)
app.include_router(proactive_router)
app.include_router(sso_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_DB = DATA_DIR / "assistant_features.db"


# ============================================================
# OUTILS COMMUNS
# ============================================================

def get_db():
    db = sqlite3.connect(FEATURES_DB, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    return " ".join(value.split()).strip(" ?!.,;:")


def require_admin(token: Optional[str]):
    expected = os.getenv("ESIC_ADMIN_TOKEN")

    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Administration désactivée : ESIC_ADMIN_TOKEN non configuré.",
        )

    if not token or token != expected:
        raise HTTPException(
            status_code=403,
            detail="Accès administrateur refusé.",
        )


def init_features_database():
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS response_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS answer_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                incorrect_answer TEXT NOT NULL,
                corrected_answer TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TEXT NOT NULL,
                reviewed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS escalation_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                question TEXT NOT NULL,
                reason TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'handled', 'rejected')),
                created_at TEXT NOT NULL
            );
            """
        )


# ============================================================
# MODÈLES DES NOUVELLES US
# ============================================================

class FeedbackRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=5000)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class KnowledgeRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    answer: str = Field(min_length=1, max_length=5000)
    category: str = Field(default="general", max_length=100)


class CorrectionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    incorrect_answer: str = Field(min_length=1, max_length=5000)
    corrected_answer: str = Field(min_length=1, max_length=5000)


class CorrectionReviewRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")


class EscalationRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=1000)
    reason: str = Field(default="", max_length=1000)


class EscalationReviewRequest(BaseModel):
    status: str = Field(pattern="^(handled|rejected)$")


# ============================================================
# RECHERCHE DANS LES CONNAISSANCES ET CORRECTIONS VALIDÉES
# ============================================================

def find_custom_answer(question: str):
    target = normalize_text(question)

    if not target:
        return None

    with get_db() as db:
        corrections = db.execute(
            """
            SELECT question, corrected_answer
            FROM answer_corrections
            WHERE status = 'approved'
            ORDER BY reviewed_at DESC, id DESC
            """
        ).fetchall()

        for row in corrections:
            if normalize_text(row["question"]) == target:
                return row["corrected_answer"]

        entries = db.execute(
            """
            SELECT question, answer
            FROM knowledge_entries
            ORDER BY id DESC
            """
        ).fetchall()

        for row in entries:
            if normalize_text(row["question"]) == target:
                return row["answer"]

    return None


# ============================================================
# INITIALISATION
# ============================================================

@app.on_event("startup")
def startup():
    init_log_database()
    init_features_database()


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {"status": "ok"}


# ============================================================
# US-002 / US-003 — CONVERSATIONS
# ============================================================

@app.post("/api/conversations", response_model=Conversation)
def new_conversation():
    return create_conversation()


@app.get("/api/conversations", response_model=ConversationListResponse)
def list_conversations():
    return ConversationListResponse(
        conversations=get_conversations()
    )


@app.get(
    "/api/conversations/{conversation_id}",
    response_model=Conversation,
)
def get_one_conversation(conversation_id: str):
    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail=("Conversation not found." if request.language == "en" else "Conversation introuvable."),
        )

    return conversation


# ============================================================
# US-001 / US-011 / US-012 / US-013 / US-032 — CHAT
# ============================================================

class Epic8ChatRequest(ChatRequest):
    # Langue envoyée par le frontend. La génération doit ensuite respecter ce choix.
    language: str = Field(default="fr", pattern="^(fr|en)$")


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: Epic8ChatRequest):
    conversation_id = request.conversation_id
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=422,
            detail=("Message cannot be empty." if request.language == "en" else "Le message ne peut pas être vide."),
        )

    if get_conversation(conversation_id) is None:
        raise HTTPException(
            status_code=404,
            detail=("Conversation not found." if request.language == "en" else "Conversation introuvable."),
        )

    # US-013 — Rate limiting
    rate_result = check_rate_limit(conversation_id)

    if not rate_result["allowed"]:
        log_security_event(
            session_id=conversation_id,
            event_type="rate_limit",
            reason="Limite de 10 questions par minute dépassée.",
            question=message,
        )
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many questions. Please wait one minute before trying again."
                if request.language == "en" else
                "Trop de questions envoyées. Veuillez patienter une minute avant de continuer."
            ),
        )

    # US-012 — Sécurité du message
    security_result = check_message_security(message)

    if not security_result["allowed"]:
        log_security_event(
            session_id=conversation_id,
            event_type=security_result["type"],
            reason=security_result["reason"],
            question=message,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "Your message was blocked because it contains a potentially unsafe or unauthorized instruction."
                if request.language == "en" else
                "Votre message a été bloqué car il contient une instruction potentiellement dangereuse ou non autorisée."
            ),
        )

    # US-011 — Logging
    log_question(
        question=message,
        session_id=conversation_id,
    )

    # Les corrections validées et connaissances personnalisées
    # sont consultées avant le moteur de réponse habituel.
    # Les questions anglaises sont traduites pour retrouver les connaissances
    # stockées en français. La réponse complète est ensuite traduite si besoin.
    lookup_question = message
    if request.language == "en":
        try:
            lookup_question = translate_text(message, target="fr", source="auto")
        except Exception:
            lookup_question = message

    custom_answer = find_custom_answer(lookup_question)

    if custom_answer:
        question = lookup_question
        if request.language == "en":
            try:
                answer = translate_text(custom_answer, target="en", source="auto")
            except Exception:
                answer = (
                    "I couldn't translate this saved answer right now. "
                    "Please try again or switch to French."
                )
        else:
            answer = custom_answer
    else:
        question = process_question(lookup_question)
        answer = generate_response(question, language=request.language)

    # Historique
    add_message(
        conversation_id=conversation_id,
        sender="user",
        text=question,
    )
    add_message(
        conversation_id=conversation_id,
        sender="bot",
        text=answer,
    )

    return ChatResponse(answer=answer)


# ============================================================
# US-002 — HISTORIQUE
# ============================================================

@app.get(
    "/api/history/{conversation_id}",
    response_model=HistoryResponse,
)
def history(conversation_id: str):
    if get_conversation(conversation_id) is None:
        raise HTTPException(
            status_code=404,
            detail=("Conversation not found." if request.language == "en" else "Conversation introuvable."),
        )

    return HistoryResponse(
        conversation_id=conversation_id,
        messages=get_history(conversation_id),
    )


def _dashboard_normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


def _dashboard_category(question: str) -> str:
    q = _dashboard_normalize(question)

    rules = {
        "Horaires": ("horaire", "heure", "ouverture", "fermeture"),
        "Calendrier": ("calendrier", "date", "vacances", "rentre"),
        "Formations": ("formation", "cours", "matiere", "diplome"),
        "Contacts": ("contact", "telephone", "email", "adresse"),
        "Règlement": ("reglement", "absence", "retard", "procedure"),
    }

    for category, keywords in rules.items():
        if any(word in q for word in keywords):
            return category

    return "Général"


def _dashboard_read_logs():
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT question, session_id, timestamp
            FROM question_logs
            ORDER BY timestamp ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _dashboard_parse_date(value: str):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        return None


@app.get("/api/dashboard/top-questions")
def dashboard_top_questions(limite: int = Query(10, ge=1, le=100)):
    logs = _dashboard_read_logs()
    counts = Counter()
    labels = {}

    for row in logs:
        question = (row.get("question") or "").strip()
        if not question:
            continue
        key = _dashboard_normalize(question)
        counts[key] += 1
        labels.setdefault(key, question)

    return {
        "top_questions": [
            {"question": labels[key], "nombre": count}
            for key, count in counts.most_common(limite)
        ]
    }


@app.get("/api/dashboard/categories")
def dashboard_categories():
    counts = Counter(
        _dashboard_category(row.get("question") or "")
        for row in _dashboard_read_logs()
    )
    return {
        "categories": [
            {"categorie": name, "nombre": count}
            for name, count in counts.most_common()
        ]
    }


@app.get("/api/dashboard/evolution")
def dashboard_evolution(jours: int = Query(14, ge=1, le=365)):
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=jours - 1)
    counts = Counter()

    for row in _dashboard_read_logs():
        dt = _dashboard_parse_date(row.get("timestamp"))
        if dt and start <= dt.date() <= today:
            counts[dt.date().isoformat()] += 1

    return {
        "evolution": [
            {
                "date": (start + timedelta(days=i)).isoformat(),
                "nombre": counts[(start + timedelta(days=i)).isoformat()],
            }
            for i in range(jours)
        ]
    }


@app.get("/api/dashboard/tendances")
def dashboard_tendances():
    today = datetime.now(timezone.utc).date()
    current_start = today - timedelta(days=6)
    previous_start = today - timedelta(days=13)
    current = Counter()
    previous = Counter()

    for row in _dashboard_read_logs():
        dt = _dashboard_parse_date(row.get("timestamp"))
        if not dt:
            continue

        date = dt.date()
        category = _dashboard_category(row.get("question") or "")

        if current_start <= date <= today:
            current[category] += 1
        elif previous_start <= date < current_start:
            previous[category] += 1

    categories = sorted(set(current) | set(previous))
    trends = []

    for category in categories:
        now = current[category]
        before = previous[category]
        evolution = (
            round((now - before) / before * 100, 1)
            if before
            else (100.0 if now else 0.0)
        )
        trends.append({
            "categorie": category,
            "questions_7_derniers_jours": now,
            "questions_7_jours_precedents": before,
            "evolution": evolution,
        })

    return {"tendances": trends}

# ============================================================
# US-024 — ÉVALUATION DES RÉPONSES
# ============================================================

@app.post("/api/feedback")
def submit_feedback(request: FeedbackRequest):
    if get_conversation(request.conversation_id) is None:
        raise HTTPException(
            status_code=404,
            detail=("Conversation not found." if request.language == "en" else "Conversation introuvable."),
        )

    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO response_feedback
                (conversation_id, question, answer, rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request.conversation_id,
                request.question.strip(),
                request.answer.strip(),
                request.rating,
                request.comment.strip(),
                now_iso(),
            ),
        )

    return {
        "message": "Merci pour votre évaluation.",
        "feedback_id": cursor.lastrowid,
    }


@app.get("/api/feedback/statistics")
def feedback_statistics(
    x_admin_token: Optional[str] = Header(default=None),
):
    require_admin(x_admin_token)

    with get_db() as db:
        summary = db.execute(
            """
            SELECT COUNT(*) AS total, AVG(rating) AS average_rating
            FROM response_feedback
            """
        ).fetchone()

        rows = db.execute(
            """
            SELECT rating, COUNT(*) AS count
            FROM response_feedback
            GROUP BY rating
            ORDER BY rating
            """
        ).fetchall()

    average = summary["average_rating"]

    return {
        "total": summary["total"],
        "average_rating": round(average, 2) if average is not None else None,
        "distribution": [
            {"rating": row["rating"], "count": row["count"]}
            for row in rows
        ],
    }


# ============================================================
# US-025 — ENRICHISSEMENT DE LA BASE DE CONNAISSANCES
# ============================================================

@app.post("/api/admin/knowledge")
def add_knowledge(
    request: KnowledgeRequest,
    x_admin_token: Optional[str] = Header(default=None),
):
    require_admin(x_admin_token)

    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO knowledge_entries
                (question, answer, category, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                request.question.strip(),
                request.answer.strip(),
                request.category.strip() or "general",
                now_iso(),
            ),
        )

    return {
        "message": "Connaissance ajoutée.",
        "knowledge_id": cursor.lastrowid,
    }


@app.get("/api/admin/knowledge")
def list_knowledge(
    x_admin_token: Optional[str] = Header(default=None),
):
    require_admin(x_admin_token)

    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, question, answer, category, created_at
            FROM knowledge_entries
            ORDER BY id DESC
            """
        ).fetchall()

    return {"entries": [dict(row) for row in rows]}


# ============================================================
# US-026 — CORRECTIONS ET VALIDATION ADMINISTRATEUR
# ============================================================

@app.post("/api/corrections")
def submit_correction(request: CorrectionRequest):
    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO answer_corrections
                (question, incorrect_answer, corrected_answer, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (
                request.question.strip(),
                request.incorrect_answer.strip(),
                request.corrected_answer.strip(),
                now_iso(),
            ),
        )

    return {
        "message": "Correction envoyée pour validation.",
        "correction_id": cursor.lastrowid,
        "status": "pending",
    }


@app.get("/api/admin/corrections")
def list_corrections(
    status: str = "pending",
    x_admin_token: Optional[str] = Header(default=None),
):
    require_admin(x_admin_token)

    if status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Statut invalide.")

    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, question, incorrect_answer, corrected_answer,
                   status, created_at, reviewed_at
            FROM answer_corrections
            WHERE status = ?
            ORDER BY id DESC
            """,
            (status,),
        ).fetchall()

    return {"corrections": [dict(row) for row in rows]}


@app.patch("/api/admin/corrections/{correction_id}")
def review_correction(
    correction_id: int,
    request: CorrectionReviewRequest,
    x_admin_token: Optional[str] = Header(default=None),
):
    require_admin(x_admin_token)

    with get_db() as db:
        cursor = db.execute(
            """
            UPDATE answer_corrections
            SET status = ?, reviewed_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (request.status, now_iso(), correction_id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Correction en attente introuvable.",
            )

    return {
        "message": "Correction mise à jour.",
        "correction_id": correction_id,
        "status": request.status,
    }


# ============================================================
# US-027 — ESCALADE VERS UN HUMAIN
# ============================================================

@app.post("/api/escalations")
def create_escalation(request: EscalationRequest):
    if get_conversation(request.conversation_id) is None:
        raise HTTPException(
            status_code=404,
            detail=("Conversation not found." if request.language == "en" else "Conversation introuvable."),
        )

    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO escalation_requests
                (conversation_id, question, reason, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (
                request.conversation_id,
                request.question.strip(),
                request.reason.strip(),
                now_iso(),
            ),
        )

    return {
        "message": "Votre demande a été enregistrée pour l'équipe ESIC.",
        "escalation_id": cursor.lastrowid,
        "status": "pending",
    }


@app.get("/api/admin/escalations")
def list_escalations(
    status: str = "pending",
    x_admin_token: Optional[str] = Header(default=None),
):
    require_admin(x_admin_token)

    if status not in {"pending", "handled", "rejected"}:
        raise HTTPException(status_code=400, detail="Statut invalide.")

    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, conversation_id, question, reason, status, created_at
            FROM escalation_requests
            WHERE status = ?
            ORDER BY id DESC
            """,
            (status,),
        ).fetchall()

    return {"escalations": [dict(row) for row in rows]}


@app.patch("/api/admin/escalations/{escalation_id}")
def review_escalation(
    escalation_id: int,
    request: EscalationReviewRequest,
    x_admin_token: Optional[str] = Header(default=None),
):
    require_admin(x_admin_token)

    with get_db() as db:
        cursor = db.execute(
            """
            UPDATE escalation_requests
            SET status = ?
            WHERE id = ? AND status = 'pending'
            """,
            (request.status, escalation_id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Demande d'escalade introuvable.",
            )

    return {
        "message": "Demande d'escalade mise à jour.",
        "escalation_id": escalation_id,
        "status": request.status,
    }
