"""Connexion à la base de données (US-002).

Sprint 1 : SQLite, rien à installer. Pour passer à PostgreSQL plus tard,
il suffira de définir la variable d'environnement DATABASE_URL, par exemple :
postgresql+psycopg://user:motdepasse@db:5432/assistant
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")

# check_same_thread=False : nécessaire pour SQLite avec FastAPI (plusieurs threads)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Crée les tables si elles n'existent pas encore."""
    from app.models import db_models  # noqa: F401  (enregistre les tables)

    Base.metadata.create_all(bind=engine)


def get_db():
    """Dépendance FastAPI : ouvre une session par requête et la referme ensuite."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
