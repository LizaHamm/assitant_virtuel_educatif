# Assistant Virtuel Éducatif

Projet transversal Scrum - Assistant Virtuel Éducatif.

## Stack MVP

- Frontend : React + Vite
- Backend : Python + FastAPI
- Versioning : Git + GitHub

## Structure

- `frontend/` : interface utilisateur
- `backend/` : API et logique serveur
- `nlp/` : composants IA/NLP
- `data/` : datasets officiels
- `tests/` : tests
- `docs/` : documentation

## Lancer le projet sans Docker

### Backend

```bash
cd backend
python -m venv .venv
```

Windows :
```bash
.venv\Scripts\activate
```

macOS/Linux :
```bash
source .venv/bin/activate
```

Puis :

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

Dans un autre terminal :

```bash
cd frontend
npm install
npm run dev
```

Ouvrir ensuite l'URL affichée par Vite, généralement :
`http://localhost:5173`

## MVP US-001

Le flux actuel est :

```text
React
  ↓
POST /api/chat
  ↓
FastAPI
  ↓
traitement de la question
  ↓
génération d'une réponse temporaire
  ↓
React
```

Les datasets officiels du professeur seront intégrés ultérieurement.

## US-002 : historique de conversation

Le navigateur génère un identifiant de session aléatoire (UUID), conservé tant que l'onglet reste ouvert.
Chaque question et sa réponse sont enregistrées en base (SQLite). Au chargement de la page,
l'historique de la session est récupéré via `GET /api/history/{session_id}` et réaffiché dans l'ordre chronologique :
un rafraîchissement de la page ne fait donc rien perdre.
