import os
import logging
import sqlite3
import time
import unicodedata
from datetime import datetime, timezone, timedelta
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
from app.services.nlp_services import analyze_question
from app.services.response_service import generate_response

# Préchargement des modèles lourds au démarrage : le premier pic de trafic ne
# doit jamais déclencher 20 chargements Sentence-BERT simultanés.
try:
    from app.services.semantic_search_service import semantic_search
except Exception as exc:
    semantic_search = None
    logging.getLogger(__name__).warning("Recherche sémantique indisponible au chargement : %r", exc)

try:
    from app.services.advanced_nlp_service import (
        analyze_advanced_nlp,
        detect_sentiment_urgency,
    )
except Exception:
    analyze_advanced_nlp = None
    detect_sentiment_urgency = None
from app.services.bilingual_service import translate_text
from app.services.history_service import (
    create_conversation,
    get_conversations,
    get_conversation,
    add_message,
    get_history,
    rename_conversation,
    delete_conversation,
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
from app.dashboard import (
    router as dashboard_router,
    init_dashboard_database,
    record_dashboard_event,
)

from collections import Counter

logger = logging.getLogger(__name__)


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
app.include_router(dashboard_router)

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
    init_dashboard_database()

    # IMPORTANT PERFORMANCE : on charge les modèles AVANT d'accepter du trafic.
    # L'ancien warm-up du test utilisait une question d'horaires, résolue par une
    # règle déterministe ; Sentence-BERT n'était donc jamais réellement chargé.
    try:
        import torch
        torch.set_num_threads(1)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass
    except Exception:
        pass

    try:
        analyze_question("Quand ont lieu les rattrapages ?")
        logger.info("Warm-up NLP classique terminé")
    except Exception:
        logger.exception("Warm-up NLP classique impossible")

    if analyze_advanced_nlp is not None:
        try:
            analyze_advanced_nlp("Quand ont lieu les rattrapages ?")
            logger.info("Warm-up NLP avancé terminé")
        except Exception:
            logger.exception("Warm-up NLP avancé impossible")

    if semantic_search is not None:
        try:
            semantic_search("Quand ont lieu les rattrapages ?", top_k=3)
            logger.info("Warm-up Sentence-BERT/FAISS terminé")
        except Exception:
            logger.exception("Warm-up Sentence-BERT/FAISS impossible")


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
            detail="Conversation introuvable.",
        )

    return conversation


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


@app.patch("/api/conversations/{conversation_id}", response_model=Conversation)
def rename_one_conversation(conversation_id: str, request: ConversationRenameRequest):
    try:
        conversation = rename_conversation(conversation_id, request.title)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
def delete_one_conversation(conversation_id: str):
    if not delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    return {"deleted": True, "conversation_id": conversation_id}


# ============================================================
# US-001 / US-011 / US-012 / US-013 / US-032 — CHAT
# ============================================================

class Epic8ChatRequest(ChatRequest):
    # Langue envoyée par le frontend. La génération doit ensuite respecter ce choix.
    language: str = Field(default="fr", pattern="^(fr|en)$")


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: Epic8ChatRequest):
    request_started = time.perf_counter()
    conversation_id = request.conversation_id
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=422,
            detail=(
                "Message cannot be empty."
                if request.language == "en"
                else "Le message ne peut pas être vide."
            ),
        )

    if get_conversation(conversation_id) is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found."
                if request.language == "en"
                else "Conversation introuvable."
            ),
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
                if request.language == "en"
                else "Trop de questions envoyées. Veuillez patienter une minute avant de continuer."
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
                if request.language == "en"
                else "Votre message a été bloqué car il contient une instruction potentiellement dangereuse ou non autorisée."
            ),
        )

    # US-011 — Logging
    # L'identifiant du log relie la question à ses métadonnées NLP dashboard.
    log_id = log_question(question=message, session_id=conversation_id)

    # La base de connaissances et le NLP travaillent en français.
    # En anglais, on traduit UNE SEULE FOIS la question, puis on réutilise
    # cette version française pour le NLP, la recherche de réponse et le moteur.
    lookup_question = message
    input_translation_ok = request.language != "en"
    if request.language == "en":
        try:
            lookup_question = translate_text(message, target="fr", source="en")
            input_translation_ok = True
        except Exception as exc:
            logger.warning("Traduction de la question entrante impossible : %r", exc)
            lookup_question = message
            input_translation_ok = False

    # US-014, US-015, US-017 et US-018 — Analyse NLP.
    # Ne pas envoyer de texte anglais aux modèles entraînés en français si la
    # traduction a échoué : leurs prédictions seraient trompeuses.
    nlp_result = None
    if input_translation_ok:
        try:
            nlp_result = analyze_question(lookup_question)
        except Exception:
            logger.exception("L'analyse NLP a échoué ; poursuite sans métadonnées NLP")
            nlp_result = None

    # US-027 / Démo finale — détection frustration / urgence.
    # Si le NLP avancé recommande une intervention humaine, on crée directement
    # une demande d'escalade au lieu d'envoyer la phrase émotionnelle dans la
    # recherche documentaire (ce qui pouvait sélectionner un document sans rapport).
    emotion_result = {}
    auto_human_escalation = False
    if input_translation_ok and detect_sentiment_urgency is not None:
        try:
            emotion_result = detect_sentiment_urgency(lookup_question) or {}
            auto_human_escalation = bool(
                emotion_result.get("human_escalation_recommended", False)
            )
        except Exception:
            logger.exception(
                "Détection sentiment/urgence impossible ; poursuite normale du chat"
            )
            emotion_result = {}
            auto_human_escalation = False

    # La recherche de réponses personnalisées utilise elle aussi le texte français.
    custom_answer = find_custom_answer(lookup_question) if input_translation_ok else None

    if not input_translation_ok and request.language == "en":
        answer = (
            "I'm temporarily unable to translate your question. Please try again, "
            "or switch to French while the translation service is unavailable."
        )

    elif auto_human_escalation:
        question = lookup_question

        # Évite de créer plusieurs demandes identiques si l'utilisateur renvoie
        # exactement le même message pendant que la première est encore en attente.
        sentiment = str(emotion_result.get("sentiment") or "non_precise")
        urgency_score = emotion_result.get("urgency_score")
        signals = emotion_result.get("signals") or {}
        reason = (
            "Escalade automatique après détection NLP — "
            f"sentiment={sentiment}; urgency_score={urgency_score}; signals={signals}"
        )

        try:
            with get_db() as db:
                existing = db.execute(
                    """
                    SELECT id
                    FROM escalation_requests
                    WHERE conversation_id = ?
                      AND question = ?
                      AND status = 'pending'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (conversation_id, message),
                ).fetchone()

                if existing is None:
                    db.execute(
                        """
                        INSERT INTO escalation_requests
                            (conversation_id, question, reason, status, created_at)
                        VALUES (?, ?, ?, 'pending', ?)
                        """,
                        (conversation_id, message, reason, now_iso()),
                    )
        except Exception:
            # Une panne de la file d'escalade ne doit pas faire tomber le chat.
            logger.exception("Création automatique de l'escalade impossible")

        answer_fr = (
            "J'ai détecté que votre message exprime une frustration importante "
            "ou une situation urgente. Votre demande a été transmise à l'équipe "
            "ESIC pour une prise en charge humaine. Vous pouvez également utiliser "
            "le bouton « Demander de l'aide humaine » sous la réponse.\n\n"
            "Si votre demande concerne un sujet précis, vous pouvez l'indiquer dans "
            "un nouveau message pendant que la demande d'aide reste enregistrée."
        )

        if request.language == "en":
            try:
                answer = translate_text(answer_fr, target="en", source="fr")
            except Exception:
                answer = (
                    "I detected significant frustration or urgency in your message. "
                    "Your request has been forwarded to the ESIC team for human support."
                )
        else:
            answer = answer_fr

    elif custom_answer:
        question = lookup_question
        if request.language == "en":
            try:
                answer = translate_text(custom_answer, target="en", source="fr")
            except Exception as exc:
                logger.warning("Traduction de la réponse personnalisée impossible : %r", exc)
                answer = (
                    "I found a relevant answer, but I couldn't translate it right now. "
                    "Please try again or switch to French."
                )
        else:
            answer = custom_answer

    elif nlp_result and nlp_result.get("clarification", {}).get("required"):
        # US-018 — Demander une précision plutôt que de deviner.
        question = lookup_question
        clarification = nlp_result["clarification"]["question"]
        if request.language == "en":
            try:
                answer = translate_text(clarification, target="en", source="fr")
            except Exception as exc:
                logger.warning("Traduction de la clarification impossible : %r", exc)
                answer = (
                    "Could you clarify your question? Are you asking about a class, "
                    "an exam, or an administrative procedure?"
                )
        else:
            answer = clarification

    else:
        # À partir d'ici, question est française. L'adaptateur est appelé en
        # français pour éviter une seconde traduction EN -> FR.
        question = process_question(lookup_question)

        # US-016 — Le résultat NLP est transmis séparément au moteur de réponse.
        # IMPORTANT : on ne concatène plus de texte technique à la question,
        # sinon ce faux texte pollue la recherche dans la base de connaissances.
        answer_fr = generate_response(
            question,
            nlp_result=nlp_result,
        )
        if request.language == "en":
            try:
                answer = translate_text(answer_fr, target="en", source="fr")
            except Exception as exc:
                logger.warning("Traduction de la réponse finale impossible : %r", exc)
                answer = (
                    "I understood your question, but I couldn't translate the answer "
                    "right now. Please try again or switch to French."
                )
        else:
            answer = answer_fr

    # Analytics : catégorie/intention NLP réellement produites + latence.
    # Une panne du dashboard ne doit jamais bloquer la réponse du chatbot.
    try:
        record_dashboard_event(
            log_id=log_id,
            session_id=conversation_id,
            question=message,
            nlp_result=nlp_result,
            response_ms=round((time.perf_counter() - request_started) * 1000, 2),
        )
    except Exception:
        logger.exception("Enregistrement dashboard impossible ; réponse conservée")

    # Historique : on conserve la question d'origine et la réponse affichée.
    add_message(
        conversation_id=conversation_id,
        sender="user",
        text=message,
    )
    add_message(
        conversation_id=conversation_id,
        sender="bot",
        text=answer,
    )

    # Les champs NLP sont facultatifs dans ChatResponse.
    if nlp_result:
        clarification_data = nlp_result["clarification"]
        return ChatResponse(
            answer=answer,
            category=nlp_result["category"],
            category_confidence=nlp_result["category_confidence"],
            intent=nlp_result["intent"],
            intent_confidence=nlp_result["intent_confidence"],
            entities=nlp_result["entities"],
            clarification_required=clarification_data["required"],
            clarification_question=clarification_data["question"],
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
            detail="Conversation introuvable.",
        )

    return HistoryResponse(
        conversation_id=conversation_id,
        messages=get_history(conversation_id),
    )


# ============================================================
# DASHBOARD ANALYTICS — US-019 À US-023
# ============================================================
# Les routes /api/dashboard/* sont regroupées dans app/dashboard.py.
# Elles utilisent les logs réels + les sorties du pipeline NLP.


# ============================================================
# US-024 — ÉVALUATION DES RÉPONSES
# ============================================================

@app.post("/api/feedback")
def submit_feedback(request: FeedbackRequest):
    if get_conversation(request.conversation_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation introuvable.",
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
            detail="Conversation introuvable.",
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
