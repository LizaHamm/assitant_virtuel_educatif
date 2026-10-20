"""Journal centralisé des interactions de la borne ESIC (US-030)."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/kiosk", tags=["Borne interactive"])

# Une borne est considérée en ligne si son dernier signal date de moins de 70 secondes.
ONLINE_WINDOW_SECONDS = 70

# Base persistante locale au backend. Peut être déplacée avec KIOSK_DB_PATH.
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "kiosk_interactions.db"
DB_PATH = Path(os.getenv("KIOSK_DB_PATH", str(DEFAULT_DB_PATH)))


class KioskInteractionIn(BaseModel):
    kiosk_id: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=80)
    conversation_id: str | None = Field(default=None, max_length=100)
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS kiosk_interactions (
            id TEXT PRIMARY KEY,
            kiosk_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            conversation_id TEXT,
            details_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            received_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_kiosk_interactions_received_at "
        "ON kiosk_interactions(received_at)"
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS kiosk_heartbeats (
            kiosk_id TEXT PRIMARY KEY,
            last_seen TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'web'
        )"""
    )
    connection.commit()
    return connection


@router.post("/interactions", status_code=201)
def record_interaction(payload: KioskInteractionIn):
    """Enregistre une interaction sans interrompre le parcours utilisateur."""
    now = datetime.now(timezone.utc).isoformat()
    occurred_at = (payload.occurred_at or datetime.now(timezone.utc)).isoformat()
    interaction_id = str(uuid4())
    details_json = json.dumps(payload.details, ensure_ascii=False, default=str)

    with _connect() as connection:
        connection.execute(
            """INSERT INTO kiosk_interactions
               (id, kiosk_id, event_type, conversation_id, details_json, occurred_at, received_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                interaction_id,
                payload.kiosk_id,
                payload.event_type,
                payload.conversation_id,
                details_json,
                occurred_at,
                now,
            ),
        )

    return {"status": "recorded", "interaction_id": interaction_id}


class KioskHeartbeatIn(BaseModel):
    kiosk_id: str = Field(min_length=1, max_length=100)
    mode: str = Field(default="web", max_length=30)


@router.post("/heartbeat")
def receive_kiosk_heartbeat(payload: KioskHeartbeatIn):
    """Met à jour le dernier signal de vie envoyé par une borne."""
    now = datetime.now(timezone.utc).isoformat()
    safe_mode = payload.mode if payload.mode in {"web", "kiosk"} else "web"
    with _connect() as connection:
        connection.execute(
            """INSERT INTO kiosk_heartbeats (kiosk_id, last_seen, mode)
               VALUES (?, ?, ?)
               ON CONFLICT(kiosk_id) DO UPDATE SET
                 last_seen = excluded.last_seen, mode = excluded.mode""",
            (payload.kiosk_id, now, safe_mode),
        )
    return {"status": "ok", "kiosk_id": payload.kiosk_id, "last_seen": now}


@router.get("/status")
def get_kiosk_statuses(x_admin_token: str | None = Header(default=None)):
    """Liste les bornes connues; endpoint réservé à l'administration."""
    expected_token = os.getenv("KIOSK_ADMIN_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="Configurez KIOSK_ADMIN_TOKEN pour activer le monitoring.")
    if not x_admin_token or x_admin_token != expected_token:
        raise HTTPException(status_code=403, detail="Jeton administrateur invalide.")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=ONLINE_WINDOW_SECONDS)
    with _connect() as connection:
        rows = connection.execute(
            """SELECT h.kiosk_id, h.last_seen, h.mode,
                      (SELECT COUNT(*) FROM kiosk_interactions i WHERE i.kiosk_id = h.kiosk_id) AS interactions_count
               FROM kiosk_heartbeats h ORDER BY h.last_seen DESC"""
        ).fetchall()

    kiosks = []
    for row in rows:
        try:
            last_seen = datetime.fromisoformat(row["last_seen"])
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            online = last_seen >= cutoff
        except (TypeError, ValueError):
            online = False
        kiosks.append({
            "kiosk_id": row["kiosk_id"],
            "last_seen": row["last_seen"],
            "mode": row["mode"],
            "status": "online" if online else "offline",
            "interactions_count": row["interactions_count"],
        })
    return {"kiosks": kiosks, "online_window_seconds": ONLINE_WINDOW_SECONDS, "checked_at": now.isoformat()}


@router.get("/health")
def kiosk_logging_health():
    """Vérifie que le stockage des interactions est accessible."""
    try:
        with _connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS total FROM kiosk_interactions"
            ).fetchone()["total"]
        return {"status": "ok", "storage": "sqlite", "total_interactions": count}
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Stockage des interactions indisponible.") from exc


@router.get("/interactions")
def list_interactions(
    limit: int = Query(default=100, ge=1, le=500),
    x_admin_token: str | None = Header(default=None),
):
    """Lecture réservée à l'administration, activée par KIOSK_ADMIN_TOKEN."""
    expected_token = os.getenv("KIOSK_ADMIN_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="Configurez KIOSK_ADMIN_TOKEN pour activer la consultation administrative.",
        )
    if not x_admin_token or x_admin_token != expected_token:
        raise HTTPException(status_code=403, detail="Jeton administrateur invalide.")

    with _connect() as connection:
        rows = connection.execute(
            """SELECT id, kiosk_id, event_type, conversation_id, details_json,
                      occurred_at, received_at
               FROM kiosk_interactions ORDER BY received_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    return {
        "interactions": [
            {
                "id": row["id"],
                "kiosk_id": row["kiosk_id"],
                "event_type": row["event_type"],
                "conversation_id": row["conversation_id"],
                "details": json.loads(row["details_json"]),
                "occurred_at": row["occurred_at"],
                "received_at": row["received_at"],
            }
            for row in rows
        ]
    }
