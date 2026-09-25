from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat():
    response = client.post(
        "/api/chat",
        json={"session_id": str(uuid4()), "message": "Bonjour"}
    )
    assert response.status_code == 200
    assert "answer" in response.json()


def test_chat_rejects_empty_message():
    response = client.post(
        "/api/chat",
        json={"session_id": str(uuid4()), "message": ""}
    )
    assert response.status_code == 422


def test_chat_rejects_whitespace_only_message():
    response = client.post(
        "/api/chat",
        json={"session_id": str(uuid4()), "message": "    "}
    )
    assert response.status_code == 400


def test_chat_requires_session_id():
    response = client.post("/api/chat", json={"message": "Bonjour"})
    assert response.status_code == 422
