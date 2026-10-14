import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_FILE = PROJECT_ROOT / "backend" / "chatbot.db"


def get_connection():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_log_database():
    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS question_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                question TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )

        connection.commit()
        connection.close()

    except Exception as error:
        print(
            f"[LOG] Impossible d'initialiser la base de logs : {error}"
        )


def get_timestamp():
    return datetime.now(timezone.utc).isoformat()


def log_question(question, session_id):
    """
    US-011
    Enregistre chaque question avec :
    - question
    - session_id
    - timestamp UTC

    Une erreur de logging ne doit jamais empêcher
    le chatbot de répondre.
    """

    try:
        connection = get_connection()

        connection.execute(
            """
            INSERT INTO question_logs (
                question,
                session_id,
                timestamp
            )
            VALUES (?, ?, ?)
            """,
            (
                question,
                session_id,
                get_timestamp(),
            ),
        )

        connection.commit()
        connection.close()

    except Exception as error:
        print(
            f"[LOG] Erreur lors de l'enregistrement de la question : {error}"
        )


def log_security_event(
    session_id,
    event_type,
    reason,
    question,
):
    """
    US-012 / US-013
    Enregistre les tentatives bloquées.
    """

    try:
        connection = get_connection()

        connection.execute(
            """
            INSERT INTO security_logs (
                session_id,
                event_type,
                reason,
                question,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                event_type,
                reason,
                question,
                get_timestamp(),
            ),
        )

        connection.commit()
        connection.close()

    except Exception as error:
        print(
            f"[SECURITY LOG] Erreur : {error}"
        )