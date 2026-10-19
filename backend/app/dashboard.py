import json
import logging
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, Query

from app.services.log_service import get_connection
from app.services.nlp_services import analyze_question

logger = logging.getLogger(__name__)
_BACKFILL_LOCK = Lock()
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_DB = DATA_DIR / "assistant_features.db"

STOPWORDS = {
    "a", "ai", "au", "aux", "avec", "ce", "ces", "cette", "comment",
    "dans", "de", "des", "du", "elle", "en", "est", "et", "faire",
    "il", "je", "la", "le", "les", "leur", "leurs", "ma", "mais",
    "me", "mes", "mon", "ne", "nous", "on", "ou", "par", "pas",
    "peut", "pour", "pourquoi", "qu", "que", "quel", "quelle", "quels",
    "quelles", "qui", "sa", "se", "ses", "son", "sur", "ta", "te",
    "tes", "ton", "tu", "un", "une", "vos", "votre", "vous", "y",
    "esic", "svp", "stp", "bonjour", "merci",
}

TOPIC_ALIASES = {
    "bibliotheque": "Bibliothèque", "scolarite": "Scolarité",
    "alternance": "Alternance", "stage": "Stage", "stages": "Stage",
    "examen": "Examens", "examens": "Examens",
    "rattrapage": "Rattrapages", "rattrapages": "Rattrapages",
    "absence": "Absences", "absences": "Absences",
    "retard": "Retards", "retards": "Retards",
    "planning": "Planning", "horaire": "Horaires", "horaires": "Horaires",
    "formation": "Formations", "formations": "Formations",
    "inscription": "Inscriptions", "inscriptions": "Inscriptions",
    "bourse": "Bourses", "bourses": "Bourses", "logement": "Logement",
    "contact": "Contacts", "contacts": "Contacts", "reglement": "Règlement",
}


def _features_connection():
    db = sqlite3.connect(FEATURES_DB, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def init_dashboard_database():
    with _features_connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS dashboard_nlp_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id INTEGER NOT NULL UNIQUE,
                session_id TEXT NOT NULL,
                question TEXT NOT NULL,
                category TEXT,
                category_confidence REAL,
                intent TEXT,
                intent_confidence REAL,
                entities_json TEXT DEFAULT '{}',
                clarification_required INTEGER NOT NULL DEFAULT 0,
                response_ms REAL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_dashboard_nlp_events_created_at
            ON dashboard_nlp_events(created_at);

            CREATE INDEX IF NOT EXISTS idx_dashboard_nlp_events_category
            ON dashboard_nlp_events(category);

            CREATE INDEX IF NOT EXISTS idx_dashboard_nlp_events_intent
            ON dashboard_nlp_events(intent);
            """
        )


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


def _parse_date(value: str):
    try:
        dt = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        return None


def _read_logs():
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, question, session_id, timestamp
            FROM question_logs
            ORDER BY timestamp ASC, id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def record_dashboard_event(
    log_id: int | None,
    session_id: str,
    question: str,
    nlp_result: dict | None,
    response_ms: float | None,
    created_at: str | None = None,
):
    """Enregistre les vraies métadonnées NLP produites pendant /api/chat."""
    if not log_id:
        return

    init_dashboard_database()
    nlp_result = nlp_result or {}
    clarification = nlp_result.get("clarification") or {}
    entities = nlp_result.get("entities") or {}

    with _features_connection() as db:
        db.execute(
            """
            INSERT INTO dashboard_nlp_events (
                log_id, session_id, question, category, category_confidence,
                intent, intent_confidence, entities_json,
                clarification_required, response_ms, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(log_id) DO UPDATE SET
                category = excluded.category,
                category_confidence = excluded.category_confidence,
                intent = excluded.intent,
                intent_confidence = excluded.intent_confidence,
                entities_json = excluded.entities_json,
                clarification_required = excluded.clarification_required,
                response_ms = COALESCE(excluded.response_ms, dashboard_nlp_events.response_ms)
            """,
            (
                int(log_id), session_id, question,
                nlp_result.get("category"), nlp_result.get("category_confidence"),
                nlp_result.get("intent"), nlp_result.get("intent_confidence"),
                json.dumps(entities, ensure_ascii=False),
                1 if clarification.get("required") else 0,
                response_ms, created_at or _now_iso(),
            ),
        )


def _cached_events():
    init_dashboard_database()
    with _features_connection() as db:
        rows = db.execute(
            """
            SELECT log_id, session_id, question, category, category_confidence,
                   intent, intent_confidence, entities_json,
                   clarification_required, response_ms, created_at
            FROM dashboard_nlp_events
            """
        ).fetchall()
    return {int(row["log_id"]): dict(row) for row in rows}


def _analyze_missing_logs(logs):
    """Ré-analyse une seule fois les anciens logs avec le vrai pipeline NLP."""
    # Plusieurs widgets du dashboard chargent en parallèle. Le verrou évite
    # que cinq requêtes tentent de ré-analyser/écrire les mêmes anciens logs.
    with _BACKFILL_LOCK:
        cached = _cached_events()
        for row in logs:
            log_id = int(row["id"])
            if log_id in cached:
                continue
            try:
                result = analyze_question(row.get("question") or "")
            except Exception:
                logger.exception("Ré-analyse NLP impossible pour le log %s", log_id)
                result = None
            try:
                record_dashboard_event(
                    log_id=log_id,
                    session_id=row.get("session_id") or "",
                    question=row.get("question") or "",
                    nlp_result=result,
                    response_ms=None,
                    created_at=row.get("timestamp") or _now_iso(),
                )
            except Exception:
                logger.exception("Cache dashboard impossible pour le log %s", log_id)
        return _cached_events()


def _rows():
    logs = _read_logs()
    events = _analyze_missing_logs(logs)
    result = []
    for log in logs:
        event = events.get(int(log["id"]), {})
        result.append({
            **log,
            "category": event.get("category") or "Non classée",
            "category_confidence": event.get("category_confidence"),
            "intent": event.get("intent") or "Non classée",
            "intent_confidence": event.get("intent_confidence"),
            "clarification_required": bool(event.get("clarification_required", 0)),
            "response_ms": event.get("response_ms"),
        })
    return result


def _escalations():
    with _features_connection() as db:
        rows = db.execute(
            """
            SELECT conversation_id, question, reason, status, created_at
            FROM escalation_requests
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _feedback():
    with _features_connection() as db:
        rows = db.execute(
            """
            SELECT rating, comment, created_at
            FROM response_feedback
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _unresolved_keys(rows):
    unresolved = {
        (row.get("session_id") or "", _normalize(row.get("question") or ""))
        for row in rows if row.get("clarification_required")
    }
    for item in _escalations():
        unresolved.add((
            item.get("conversation_id") or "",
            _normalize(item.get("question") or ""),
        ))
    return unresolved


def _topic_tokens(question: str):
    words = re.findall(r"[a-z0-9][a-z0-9_-]{2,}", _normalize(question))
    topics = []
    for word in words:
        if word in STOPWORDS or word.isdigit():
            continue
        topics.append(TOPIC_ALIASES.get(word, word.capitalize()))
    return topics


@router.get("/overview")
def overview():
    rows = _rows()
    feedback = _feedback()
    unresolved = _unresolved_keys(rows)
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    questions_24h = sum(
        1 for row in rows
        if (dt := _parse_date(row.get("timestamp"))) and dt >= last_24h
    )
    sessions = len({row.get("session_id") for row in rows if row.get("session_id")})

    ratings = [int(item["rating"]) for item in feedback if item.get("rating") is not None]
    average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    satisfaction_rate = (
        round(sum(1 for rating in ratings if rating >= 4) / len(ratings) * 100, 1)
        if ratings else None
    )

    latencies = [float(row["response_ms"]) for row in rows if row.get("response_ms") is not None]
    average_response_ms = round(sum(latencies) / len(latencies), 1) if latencies else None

    category_confidences = [
        float(row["category_confidence"]) for row in rows
        if row.get("category_confidence") is not None
    ]
    intent_confidences = [
        float(row["intent_confidence"]) for row in rows
        if row.get("intent_confidence") is not None
    ]

    unresolved_count = sum(
        1 for row in rows
        if (row.get("session_id") or "", _normalize(row.get("question") or "")) in unresolved
    )
    resolution_rate = (
        round((len(rows) - unresolved_count) / len(rows) * 100, 1)
        if rows else None
    )

    hour_counts = Counter()
    for row in rows:
        dt = _parse_date(row.get("timestamp"))
        if dt:
            hour_counts[dt.hour] += 1
    peak_hour = None
    peak_hour_count = 0
    if hour_counts:
        peak_hour, peak_hour_count = max(hour_counts.items(), key=lambda item: (item[1], -item[0]))

    return {
        "total_questions": len(rows),
        "questions_24h": questions_24h,
        "sessions": sessions,
        "average_rating": average_rating,
        "satisfaction_rate": satisfaction_rate,
        "resolution_rate": resolution_rate,
        "average_response_ms": average_response_ms,
        "average_category_confidence": (
            round(sum(category_confidences) / len(category_confidences) * 100, 1)
            if category_confidences else None
        ),
        "average_intent_confidence": (
            round(sum(intent_confidences) / len(intent_confidences) * 100, 1)
            if intent_confidences else None
        ),
        "feedback_count": len(ratings),
        "unresolved_count": unresolved_count,
        "peak_hour": f"{peak_hour:02d}:00" if peak_hour is not None else None,
        "peak_hour_count": peak_hour_count,
    }


@router.get("/top-questions")
def top_questions(limite: int = Query(10, ge=1, le=100)):
    counts, labels = Counter(), {}
    for row in _read_logs():
        question = (row.get("question") or "").strip()
        if not question:
            continue
        key = _normalize(question)
        counts[key] += 1
        labels.setdefault(key, question)
    return {"top_questions": [
        {"question": labels[key], "nombre": count}
        for key, count in counts.most_common(limite)
    ]}


@router.get("/categories")
def categories():
    counts = Counter(row.get("category") or "Non classée" for row in _rows())
    return {"categories": [
        {"categorie": name, "nombre": count}
        for name, count in counts.most_common()
    ]}


@router.get("/intents")
def intents():
    counts = Counter(row.get("intent") or "Non classée" for row in _rows())
    return {"intents": [
        {"intent": name, "nombre": count}
        for name, count in counts.most_common()
    ]}


@router.get("/evolution")
def evolution(jours: int = Query(14, ge=1, le=365)):
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=jours - 1)
    counts = Counter()
    for row in _read_logs():
        dt = _parse_date(row.get("timestamp"))
        if dt and start <= dt.date() <= today:
            counts[dt.date().isoformat()] += 1
    return {"evolution": [
        {"date": (start + timedelta(days=i)).isoformat(),
         "nombre": counts[(start + timedelta(days=i)).isoformat()]}
        for i in range(jours)
    ]}


@router.get("/hourly")
def hourly(heures: int = Query(24, ge=1, le=168)):
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    start = current_hour - timedelta(hours=heures - 1)
    counts = Counter()
    for row in _read_logs():
        dt = _parse_date(row.get("timestamp"))
        if not dt or dt < start:
            continue
        bucket = dt.replace(minute=0, second=0, microsecond=0)
        counts[bucket.isoformat()] += 1
    return {"hourly": [
        {
            "heure": (start + timedelta(hours=i)).isoformat(),
            "label": (start + timedelta(hours=i)).strftime("%H:%M"),
            "nombre": counts[(start + timedelta(hours=i)).isoformat()],
        }
        for i in range(heures)
    ]}


@router.get("/peak-hours")
def peak_hours():
    counts = Counter()
    for row in _read_logs():
        dt = _parse_date(row.get("timestamp"))
        if dt:
            counts[dt.hour] += 1
    return {"heures": [
        {"heure": f"{hour:02d}:00", "nombre": counts[hour]}
        for hour in range(24)
    ]}


@router.get("/tendances")
def tendances():
    today = datetime.now(timezone.utc).date()
    current_start = today - timedelta(days=6)
    previous_start = today - timedelta(days=13)
    current, previous = Counter(), Counter()
    for row in _rows():
        dt = _parse_date(row.get("timestamp"))
        if not dt:
            continue
        category = row.get("category") or "Non classée"
        if current_start <= dt.date() <= today:
            current[category] += 1
        elif previous_start <= dt.date() < current_start:
            previous[category] += 1

    trends = []
    for category in set(current) | set(previous):
        now_count, before = current[category], previous[category]
        change = round((now_count - before) / before * 100, 1) if before else (100.0 if now_count else 0.0)
        trends.append({
            "categorie": category,
            "questions_7_derniers_jours": now_count,
            "questions_7_jours_precedents": before,
            "evolution": change,
        })
    trends.sort(key=lambda item: (item["questions_7_derniers_jours"], item["evolution"]), reverse=True)
    return {"tendances": trends}


@router.get("/emerging-topics")
def emerging_topics(limite: int = Query(8, ge=1, le=30)):
    today = datetime.now(timezone.utc).date()
    current_start = today - timedelta(days=6)
    previous_start = today - timedelta(days=13)
    current, previous = Counter(), Counter()

    for row in _read_logs():
        dt = _parse_date(row.get("timestamp"))
        if not dt:
            continue
        target = current if current_start <= dt.date() <= today else (
            previous if previous_start <= dt.date() < current_start else None
        )
        if target is None:
            continue
        for topic in set(_topic_tokens(row.get("question") or "")):
            target[topic] += 1

    topics = []
    for topic in set(current) | set(previous):
        now_count, before = current[topic], previous[topic]
        if now_count <= 0:
            continue
        delta = now_count - before
        change = round(delta / before * 100, 1) if before else 100.0
        topics.append({
            "sujet": topic,
            "questions_7_derniers_jours": now_count,
            "questions_7_jours_precedents": before,
            "variation": delta,
            "evolution": change,
        })
    topics.sort(key=lambda item: (item["variation"], item["questions_7_derniers_jours"]), reverse=True)
    return {"sujets": topics[:limite]}


@router.get("/unresolved")
def unresolved(limite: int = Query(10, ge=1, le=50)):
    rows = _rows()
    escalation_map = {
        (item.get("conversation_id") or "", _normalize(item.get("question") or "")): item
        for item in _escalations()
    }
    result, seen = [], set()
    for row in reversed(rows):
        key = (row.get("session_id") or "", _normalize(row.get("question") or ""))
        escalation = escalation_map.get(key)
        if not escalation and not row.get("clarification_required"):
            continue
        if key in seen:
            continue
        seen.add(key)
        reason = (
            (escalation.get("reason") or "Escalade vers un humain")
            if escalation else "Question ambiguë : clarification demandée"
        )
        result.append({
            "question": row.get("question") or "",
            "categorie": row.get("category") or "Non classée",
            "raison": reason,
            "date": escalation.get("created_at") if escalation else row.get("timestamp"),
        })
        if len(result) >= limite:
            break
    return {"questions_non_resolues": result}


@router.get("/feedback-summary")
def feedback_summary():
    feedback = _feedback()
    counts = Counter(int(row["rating"]) for row in feedback if row.get("rating") is not None)
    total = sum(counts.values())
    average = (
        round(sum(rating * count for rating, count in counts.items()) / total, 2)
        if total else None
    )
    satisfaction = (
        round(sum(count for rating, count in counts.items() if rating >= 4) / total * 100, 1)
        if total else None
    )
    return {
        "total": total,
        "average_rating": average,
        "satisfaction_rate": satisfaction,
        "distribution": [{"rating": rating, "count": counts[rating]} for rating in range(1, 6)],
    }
