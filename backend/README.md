# Backend - Assistant Virtuel Éducatif

## Installation

```bash
cd backend
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Puis :

```bash
pip install -r requirements.txt
```

## Lancer l'API

```bash
uvicorn app.main:app --reload
```

API :
- http://127.0.0.1:8000
- Documentation Swagger : http://127.0.0.1:8000/docs

## Endpoints MVP

### GET /health

Vérifie que le backend fonctionne.

### POST /api/chat

Exemple :

```json
{
  "session_id": "3f1c9a2e-7b4d-4c8e-9f21-5a6b7c8d9e0f",
  "message": "Bonjour"
}
```

`session_id` est un UUID généré par le navigateur. Tout autre format est refusé (erreur 422).
Un message composé uniquement d'espaces est refusé (erreur 400).
Chaque échange question-réponse est enregistré en base pour l'historique (US-002).

Réponse :

```json
{
  "answer": "Bonjour ! Comment puis-je vous aider ?"
}
```

Les réponses actuelles sont temporaires : les datasets officiels du professeur seront intégrés plus tard.

### GET /api/history/{session_id}

Renvoie l'historique d'une session, du plus ancien au plus récent (US-002).

```json
{
  "session_id": "3f1c9a2e-7b4d-4c8e-9f21-5a6b7c8d9e0f",
  "messages": [
    {
      "question": "Bonjour",
      "answer": "Bonjour ! Comment puis-je vous aider ?",
      "created_at": "2026-09-25T10:26:13.184986Z"
    }
  ]
}
```

Les dates sont en UTC. Une session inconnue renvoie une liste vide. Un identifiant qui n'est pas un UUID renvoie une erreur 422.
Par sécurité, aucune route ne permet de lister toutes les sessions.

## Base de données

Sprint 1 : SQLite, fichier `chat.db` créé automatiquement au premier lancement (ignoré par Git).
Pour utiliser une autre base (PostgreSQL au Sprint 2), définir la variable `DATABASE_URL`.

La table `chat_exchanges` (session_id, question, answer, created_at) est partagée avec US-011 :
les colonnes de journalisation (catégorie, confiance, blocage) y seront ajoutées.

## Tests

```bash
python -m pytest -v
```

Les tests utilisent une base SQLite en mémoire et ne modifient jamais `chat.db`.
