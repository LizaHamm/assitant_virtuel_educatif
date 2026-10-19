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
  "message": "Bonjour"
}
```

Réponse :

```json
{
  "answer": "Bonjour ! Comment puis-je vous aider ?"
}
```

Les réponses actuelles sont temporaires : les datasets officiels du professeur seront intégrés plus tard.
