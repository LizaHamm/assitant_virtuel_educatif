from datetime import datetime
from typing import Dict, List
from uuid import uuid4


# toutes les conversations du serveur
conversations: Dict[str, dict] = {}


def create_conversation() -> dict:
    """Crée une nouvelle conversation."""

    conversation_id = str(uuid4())
    now = datetime.now().isoformat()

    conversation = {
        "id": conversation_id,
        "title": "Nouvelle conversation",
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }

    conversations[conversation_id] = conversation

    return conversation


def get_conversations() -> List[dict]:
    """Retourne toutes les conversations, de la plus récente à la plus ancienne."""

    return sorted(
        conversations.values(),
        key=lambda conversation: conversation["updated_at"],
        reverse=True,
    )


def get_conversation(conversation_id: str) -> dict | None:
    """Retourne une conversation."""

    return conversations.get(conversation_id)


def add_message(
    conversation_id: str,
    sender: str,
    text: str,
) -> dict:
    """Ajoute un message à une conversation."""

    conversation = conversations.get(conversation_id)

    if conversation is None:
        raise ValueError("Conversation introuvable.")

    now = datetime.now()

    message = {
        "id": str(uuid4()),
        "sender": sender,
        "text": text,
        "time": now.strftime("%H:%M"),
    }

    conversation["messages"].append(message)
    conversation["updated_at"] = now.isoformat()

    #le titre devient la première question posée.
    if (
        sender == "user"
        and conversation["title"] == "Nouvelle conversation"
    ):
        conversation["title"] = text[:45]

        if len(text) > 45:
            conversation["title"] += "..."

    return message


def get_history(conversation_id: str) -> List[dict]:
    """Retourne les messages dans l'ordre chronologique."""

    conversation = conversations.get(conversation_id)

    if conversation is None:
        return []

    return conversation["messages"]