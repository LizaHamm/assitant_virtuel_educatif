# 🚀 GUIDE — Assistant Virtuel Éducatif ESIC

Ce fichier explique comment installer, lancer et utiliser le projet en local.

---

## 📁 Structure du projet

```text
assistant_virtuel_educatif/
│
├── frontend/        -> Interface React
├── backend/         -> API Python / FastAPI
├── nlp/             -> Partie NLP (prévue pour la suite)
├── data/            -> Données du projet
├── tests/           -> Tests
├── docs/            -> Documentation
│
├── README.md
└── GUIDE.md         -> Ce guide
```

---

# 1️⃣ PRÉREQUIS

Installer :

- Python
- Node.js
- npm
- Git

Vérifier les installations :

```powershell
python --version
node --version
npm.cmd --version
git --version
```

---

# 2️⃣ RÉCUPÉRER LE PROJET

Cloner le repository :

```powershell
git clone <URL_DU_REPOSITORY>
```

Entrer dans le projet :

```powershell
cd assistant_virtuel_educatif
```

---

# 3️⃣ 🐍 LANCER LE BACKEND

Le backend utilise **Python + FastAPI**.

## Étape 1 — Aller dans backend

```powershell
cd backend
```

## Étape 2 — Créer l'environnement virtuel

À faire uniquement la première fois :

```powershell
python -m venv .venv
```

## Étape 3 — Activer l'environnement virtuel

```powershell
.\\.venv\\Scripts\\Activate.ps1
```

Si PowerShell bloque l'activation :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Puis :

```powershell
.\\.venv\\Scripts\\Activate.ps1
```

Quand l'environnement est activé, le terminal affiche généralement :

```text
(.venv)
```

## Étape 4 — Installer les dépendances

À faire uniquement la première fois :

```powershell
pip install -r requirements.txt
```

## Étape 5 — Lancer le serveur

```powershell
python -m uvicorn app.main:app --reload
```

Le backend fonctionne alors sur :

```text
http://127.0.0.1:8000
```

### Documentation de l'API

```text
http://127.0.0.1:8000/docs
```

### Vérifier le serveur

```text
http://127.0.0.1:8000/health
```

Si le serveur fonctionne, on obtient :

```json
{
  "status": "ok"
}
```

⚠️ Garder ce terminal ouvert.

---

# 4️⃣ ⚛️ LANCER LE FRONTEND

Ouvrir un **deuxième terminal PowerShell**.

Depuis la racine du projet :

```powershell
cd frontend
```

## Installer les dépendances

À faire uniquement la première fois :

```powershell
npm.cmd install
```

## Lancer le frontend

```powershell
npm.cmd run dev
```

Le frontend sera disponible sur :

```text
http://localhost:5173/
```

Ouvrir cette adresse dans le navigateur.

⚠️ Le backend doit être lancé en même temps.

---

# 5️⃣ 🔄 FONCTIONNEMENT DU PROJET

```text
             Navigateur
                  │
                  │
                  ▼
        ┌──────────────────┐
        │     FRONTEND     │
        │      React       │
        │ localhost:5173   │
        └────────┬─────────┘
                 │
                 │ POST /api/chat
                 ▼
        ┌──────────────────┐
        │     BACKEND      │
        │     FastAPI      │
        │ 127.0.0.1:8000   │
        └────────┬─────────┘
                 │
                 ▼
       Traitement question
                 │
                 ▼
       Génération réponse
                 │
                 ▼
        Réponse au frontend
```

---

# 6️⃣ 💬 TESTER LE CHATBOT

Une fois les deux serveurs lancés :

1. Ouvrir :

```text
http://localhost:5173/
```

2. Écrire une question dans la barre de saisie.

3. Cliquer sur le bouton d'envoi ou appuyer sur Entrée.

4. Le frontend envoie la question au backend :

```text
POST /api/chat
```

5. Le backend traite la question et renvoie une réponse.

---

# 7️⃣ 🛑 ARRÊTER LES SERVEURS

Dans chaque terminal :

```text
Ctrl + C
```

---

# 8️⃣ 🔧 COMMANDES À RETENIR

## Backend

À partir de la racine :

```powershell
cd backend
.\\.venv\\Scripts\\Activate.ps1
python -m uvicorn app.main:app --reload
```

## Frontend

Dans un deuxième terminal :

```powershell
cd frontend
npm.cmd run dev
```

---

# 9️⃣ 🔀 GIT — RÉCUPÉRER LES MODIFICATIONS

Avant de commencer à travailler :

```powershell
git pull
```

Vérifier l'état du projet :

```powershell
git status
```

---

# 🔟 🌿 CRÉER UNE BRANCHE

Créer une branche pour travailler sur une fonctionnalité :

```powershell
git checkout -b feature/nom-de-la-fonctionnalite
```

Exemple :

```powershell
git checkout -b feature/amelioration-interface
```

---

# 1️⃣1️⃣ 💾 ENREGISTRER SON TRAVAIL

Vérifier les modifications :

```powershell
git status
```

Ajouter les fichiers :

```powershell
git add .
```

Créer un commit :

```powershell
git commit -m "feat: description de la modification"
```

Envoyer la branche sur GitHub :

```powershell
git push -u origin feature/nom-de-la-fonctionnalite
```

---

# 1️⃣2️⃣ ⚠️ PROBLÈMES FRÉQUENTS

## `npm` ne fonctionne pas

Sous PowerShell, utiliser :

```powershell
npm.cmd install
```

et :

```powershell
npm.cmd run dev
```

---

## `uvicorn` est bloqué

Utiliser :

```powershell
python -m uvicorn app.main:app --reload
```

au lieu de :

```powershell
uvicorn app.main:app --reload
```

---

## PowerShell bloque l'activation de `.venv`

Utiliser :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Puis :

```powershell
.\\.venv\\Scripts\\Activate.ps1
```

---

## Le frontend ne reçoit pas de réponse

Vérifier que le backend fonctionne :

```text
http://127.0.0.1:8000/health
```

Puis vérifier que le frontend fonctionne :

```text
http://localhost:5173/
```

Les **deux serveurs doivent être lancés simultanément**.

---

## `Not Found` sur `http://127.0.0.1:8000/`

Ce n'est pas forcément une erreur.

Le backend n'a pas besoin d'avoir une page d'accueil `/`.

Utiliser :

```text
http://127.0.0.1:8000/docs
```

pour accéder à la documentation de l'API.

Ou :

```text
http://127.0.0.1:8000/health
```

pour vérifier son fonctionnement.

---

# 1️⃣3️⃣ 📦 SI LE PROJET EST DÉJÀ INSTALLÉ

Si les dépendances sont déjà présentes, il n'est pas nécessaire de refaire :

```powershell
python -m venv .venv
pip install -r requirements.txt
npm.cmd install
```

Pour simplement travailler sur le projet :

### Terminal 1 — Backend

```powershell
cd backend
.\\.venv\\Scripts\\Activate.ps1
python -m uvicorn app.main:app --reload
```

### Terminal 2 — Frontend

```powershell
cd frontend
npm.cmd run dev
```

Puis ouvrir :

```text
http://localhost:5173/
```

---

# ✅ RÉSUMÉ ULTRA RAPIDE

## Terminal 1 — Backend

```powershell
cd backend
.\\.venv\\Scripts\\Activate.ps1
python -m uvicorn app.main:app --reload
```

## Terminal 2 — Frontend

```powershell
cd frontend
npm.cmd run dev
```

## Navigateur

```text
http://localhost:5173/
```

---

# 📌 IMPORTANT POUR LE PROJET

Pour l'instant, cette version correspond au prototype de l'US-001.

Le backend utilise actuellement des réponses temporaires/mock.

Les fonctionnalités NLP, base de données, analytics et autres User Stories seront intégrées progressivement selon le backlog du projet.
