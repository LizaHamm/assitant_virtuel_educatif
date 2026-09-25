"""Tables de la base de données.

La table chat_exchanges sert à la fois :
- à US-002 (historique de conversation par session) ;
- à US-011 (journalisation horodatée de toutes les questions).
Pour US-011, il suffira d'y ajouter les colonnes category, confidence,
blocked et block_reason, plutôt que de créer une seconde table.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatExchange(Base):
    __tablename__ = "chat_exchanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # UUID aléatoire généré par le navigateur : aucune donnée personnelle (RGPD)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
