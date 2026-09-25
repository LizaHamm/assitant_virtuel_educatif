"""Stockage et récupération de l'historique des conversations (US-002)."""
from datetime import timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import ChatExchange

# Garde-fou : une session ne renvoie jamais plus de N échanges
MAX_HISTORY_ITEMS = 200


def save_exchange(db: Session, session_id: UUID, question: str, answer: str) -> ChatExchange:
    exchange = ChatExchange(session_id=str(session_id), question=question, answer=answer)
    db.add(exchange)
    db.commit()
    db.refresh(exchange)
    return exchange


def get_history(db: Session, session_id: UUID) -> list[ChatExchange]:
    """Renvoie les échanges d'une seule session, du plus ancien au plus récent.

    Le tri se fait sur l'id auto-incrémenté : deux messages envoyés dans la même
    seconde restent ainsi toujours dans le bon ordre.
    """
    query = (
        select(ChatExchange)
        .where(ChatExchange.session_id == str(session_id))
        .order_by(ChatExchange.id)
        .limit(MAX_HISTORY_ITEMS)
    )
    exchanges = list(db.scalars(query))

    # SQLite ne conserve pas le fuseau horaire : on rappelle que les dates sont en UTC,
    # pour que le navigateur les convertisse correctement en heure locale.
    for exchange in exchanges:
        if exchange.created_at.tzinfo is None:
            exchange.created_at = exchange.created_at.replace(tzinfo=timezone.utc)
    return exchanges
