
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parents[2] / "chatbot.db"


def init_feedback_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS response_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_feedback(conversation_id, question, answer, rating, comment=None):
    comment = (comment or "").strip()[:1000]

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            INSERT INTO response_feedback
            (conversation_id, question, answer, rating, comment)
            VALUES (?, ?, ?, ?, ?)
        """, (conversation_id, question, answer, rating, comment))

        conn.commit()
        return cursor.lastrowid


def feedback_statistics():
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("""
            SELECT COUNT(*), ROUND(AVG(rating), 2)
            FROM response_feedback
        """).fetchone()

    return {
        "total": row[0],
        "average_rating": row[1]
    }
