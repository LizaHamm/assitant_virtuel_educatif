"""Tests de l'US-002 : historique de conversation."""
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def ask(session_id, message):
    response = client.post("/api/chat", json={"session_id": session_id, "message": message})
    assert response.status_code == 200
    return response.json()["answer"]


def test_new_session_has_empty_history():
    session_id = str(uuid4())
    response = client.get(f"/api/history/{session_id}")
    assert response.status_code == 200
    assert response.json() == {"session_id": session_id, "messages": []}


def test_history_is_in_chronological_order():
    session_id = str(uuid4())
    questions = ["Bonjour", "Où est la bibliothèque ?", "Merci"]
    answers = [ask(session_id, q) for q in questions]

    messages = client.get(f"/api/history/{session_id}").json()["messages"]

    assert [m["question"] for m in messages] == questions
    assert [m["answer"] for m in messages] == answers
    dates = [m["created_at"] for m in messages]
    assert dates == sorted(dates)


def test_sessions_are_isolated():
    session_a, session_b = str(uuid4()), str(uuid4())
    ask(session_a, "Question de A")
    ask(session_b, "Question de B")

    history_a = client.get(f"/api/history/{session_a}").json()["messages"]
    assert [m["question"] for m in history_a] == ["Question de A"]


def test_history_stores_cleaned_question():
    session_id = str(uuid4())
    ask(session_id, "  Bonjour    tout   le monde  ")
    messages = client.get(f"/api/history/{session_id}").json()["messages"]
    assert messages[0]["question"] == "Bonjour tout le monde"


def test_history_rejects_invalid_session_id():
    response = client.get("/api/history/pas-un-uuid")
    assert response.status_code == 422


def test_history_dates_are_utc():
    session_id = str(uuid4())
    ask(session_id, "Bonjour")
    created_at = client.get(f"/api/history/{session_id}").json()["messages"][0]["created_at"]
    assert created_at.endswith("Z") or created_at.endswith("+00:00")
