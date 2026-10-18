# ESIC Assistant — Assistant Virtuel Éducatif

Assistant virtuel éducatif développé dans le cadre du projet transverse **ESIC / ESIS-2 / CPDIA-2**.

ESIC Assistant est une application web permettant aux étudiants d'obtenir rapidement des informations sur les formations, les emplois du temps, les procédures administratives, les services du campus, les contacts, le règlement et la vie étudiante.

Le projet repose sur une architecture **React + FastAPI** et intègre une base de connaissances, des traitements NLP, une recherche hybride lexicale et sémantique avec **Sentence-BERT + FAISS**, un dashboard analytique, un système de feedback, une interface d'administration et un mode borne interactive.

> **Attention :** ce projet est un prototype pédagogique. Les données utilisées dans la base de connaissances ne constituent pas une source institutionnelle ESIC de production.

---

# Sommaire

1. Fonctionnalités
2. Technologies
3. Architecture
4. Structure du projet
5. Prérequis
6. Installation
7. Configuration des jetons
8. Installation NLP
9. Recherche sémantique
10. Traduction français / anglais
11. Lancement du projet
12. Fonctionnement du chatbot
13. Base de connaissances
14. Administration
15. Dashboard
16. Mode borne
17. Sécurité
18. Tests
19. Tests de performance
20. API
21. Git
22. `.gitignore`
23. Dépannage
24. Démarrage rapide

---

# 1. Fonctionnalités

## Chatbot

L'application permet notamment :

- de poser des questions à l'assistant ;
- de créer plusieurs conversations ;
- de consulter l'historique des conversations ;
- d'utiliser des suggestions de questions ;
- d'obtenir des réponses issues de la base de connaissances ESIC ;
- d'utiliser l'application en français ou en anglais ;
- de demander une assistance humaine ;
- d'évaluer une réponse.

Les principaux domaines couverts sont :

- orientation et formations ;
- services du campus ;
- emplois du temps et planning ;
- règlement et vie étudiante ;
- procédures administratives ;
- contacts et informations générales.

---

## Recherche d'information

Le moteur de réponse combine plusieurs méthodes :

```text
Question utilisateur
        │
        ▼
Règles déterministes
        │
        ▼
Recherche lexicale
        │
        ├───────────────┐
        ▼               ▼
Résultat fiable     Recherche sémantique
                        │
                        ▼
                  Sentence-BERT
                        │
                        ▼
                      FAISS
                        │
        ┌───────────────┘
        ▼
Reranking hybride
        │
        ▼
Meilleure réponse
```

Cette architecture permet d'éviter l'utilisation systématique du modèle sémantique lorsqu'une réponse fiable peut déjà être obtenue rapidement.

---

## Base de connaissances

Le chatbot exploite différentes sources :

- FAQ ;
- procédures administratives ;
- contacts ;
- emplois du temps ;
- documents du projet ;
- connaissances ajoutées depuis l'administration.

---

## Feedback

Les utilisateurs peuvent :

- attribuer une note à une réponse ;
- ajouter un commentaire ;
- signaler une mauvaise réponse ;
- proposer une correction ;
- demander une assistance humaine.

---

## Administration

Une interface d'administration permet notamment :

- de consulter les statistiques ;
- de consulter les feedbacks ;
- d'ajouter des connaissances ;
- de consulter les corrections proposées ;
- d'approuver ou rejeter une correction ;
- de consulter les demandes d'assistance humaine ;
- de marquer une demande comme traitée ;
- de surveiller les bornes interactives.

---

## Dashboard

Le dashboard permet notamment de suivre :

- les questions les plus fréquentes ;
- la répartition des questions par catégorie ;
- l'évolution du volume de questions ;
- les tendances ;
- les feedbacks ;
- la satisfaction utilisateur.

---

## Mode borne

Un mode borne permet d'utiliser le chatbot depuis une interface simplifiée.

Il comprend notamment :

- interface tactile simplifiée ;
- catégories rapides ;
- saisie vocale ;
- journalisation des interactions ;
- heartbeat de la borne ;
- monitoring depuis l'administration.

---

# 2. Technologies

## Frontend

```text
React
Vite
JavaScript / JSX
CSS
Web Speech API
```

## Backend

```text
Python
FastAPI
Uvicorn
Pydantic
SQLite
```

## Machine Learning / recherche

```text
scikit-learn
TF-IDF
Logistic Regression
spaCy
Sentence-Transformers
FAISS
PyTorch
```

## Modèle spaCy

```text
fr_core_news_md
```

## Modèle Sentence-Transformers

```text
paraphrase-multilingual-MiniLM-L12-v2
```

## Traduction

```text
Argos Translate
deep-translator
```

---

# 3. Architecture

```text
┌──────────────────────────────────────────────┐
│                 UTILISATEUR                  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     FRONTEND    │
              │  React + Vite   │
              │    port 5173    │
              └────────┬────────┘
                       │
                       │ API REST
                       ▼
              ┌─────────────────┐
              │     BACKEND     │
              │     FastAPI     │
              │    port 8000    │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
     Sécurité       Services      Historique
    Rate Limit       métier         SQLite
     Logging
         │             │
         └──────┬──────┘
                ▼
        MOTEUR DE RÉPONSE
                │
       ┌────────┴────────┐
       ▼                 ▼
   Recherche         Recherche
    lexicale         sémantique
                         │
                         ▼
                  Sentence-BERT
                         │
                         ▼
                       FAISS
       │                 │
       └────────┬────────┘
                ▼
          Reranking hybride
                │
                ▼
       Base de connaissances
                │
                ▼
             Réponse
```

---

# 4. Structure du projet

Structure principale :

```text
assistant_virtuel_educatif/
│
├── backend/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── dashboard.py
│   │   ├── kiosk.py
│   │   │── notifications.py
│   │   │── proactive.py
│   │   │── sso.py
│   │   │
│   │   ├── models/
│   │   │   └── chat.py
│   │   │
│   │   └── services/
│   │       ├── advanced_nlp_service.py
│   │       ├── bilingual_service.py
│   │       ├── feedback_service.py
│   │       ├── history_service.py
│   │       ├── knowledge_service.py
│   │       ├── log_service.py
│   │       ├── nlp_services.py
│   │       ├── question_service.py
│   │       ├── rate_limit_service.py
│   │       ├── response_service.py
│   │       ├── security_service.py
│   │       └── semantic_search_service.py
│   │
│   ├── data/
│   │   ├── assistant_features.db
│   │   └── kiosk_interactions.db
│   │
│   ├── scripts/
│   │   ├── build_semantic_index.py
│   │   ├── install_translation_models.py
│   │   ├── train_semantic_intent.py
│   │   └── train_nlp_models.py
│   │   
│   │
│   ├── tests/
│   │   ├── test_nlp.py
│   │   ├── test_nlp_kb.py
│   │   ├── test_hybrid_response.py
│   │   ├── test_dashboard.py
│   │   ├── test_chat.py
│   │   ├── test_semantic_search.py
│   │   ├── test_security.py
│   │   └── test_performance.py
│   │
│   │── chatbot.db
│   │
│   └── requirements.txt
│
├── frontend/
│   │
│   ├── public/
│   │   └── esic-logo.png
│   │
│   ├── components/
│   │   └── ResponsiveFeedback.jsx
│   │   
│   ├── src/
│   │   ├── App.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Dashboard.css
│   │   ├── main.jsx
│   │   └── styles.css
│   │
│   ├── index.html
│   ├── package.json
│   └── package-lock.json
│
├── data/
│   ├── faq_complete.json
│   ├── procedures_esic.json
│   ├── annuaire_contacts.json
│   ├── emploi_du_temps.json
│   ├── emploi_du_temps_exclusive.csv
│   ├── nlp_training.csv
│   │── PROCÉDURES ADMINISTRATIVES ET ACADÉMIQUES ESIC.pdf
│   │── Les données utiles pour le projet Assistant virtuel campus.pdf
│   │── Règlement Intérieur Projet Assistant Virtuel Campus.pdf
│   │── Guide de l etudiant Projet Assistant Virtuel Educatif exclusif.pdf
│   └── semantic_intent_training.csv
│
├── models/
│   │
│   ├── nlp/
│   │   ├── category_model.joblib
│   │   ├── intent_model.joblib
│   │   ├── labels.json
│   │   ├── semantic_intent_model.joblib
│   │   └── semantic_intent_training.csv
│   │
│   └── semantic_search/
│       ├── esic_knowledge.faiss
│       └── esic_knowledge_documents.json
│
├── docs/
│
├── .gitignore
└── README.md
```

Les bases SQLite et certains modèles peuvent être générés localement et ne doivent pas nécessairement être versionnés.

---

# 5. Prérequis

Installer :

```text
Python 3.11 recommandé
Node.js
npm
Git
```

Vérifier les installations :

```powershell
python --version
node --version
npm.cmd --version
git --version
```

---

# 6. Installation

## 6.1 Cloner le dépôt

```powershell
git clone "URL_DU_REPOSITORY"
cd assistant_virtuel_educatif
```

Remplacer :

```text
"URL_DU_REPOSITORY"
```

par l'adresse réelle du dépôt Git.

---

## 6.2 Installer le backend

```powershell
cd backend
python -m venv .venv
```

Activer l'environnement virtuel :

```powershell
.\.venv\Scripts\Activate.ps1
```

Mettre pip à jour :

```powershell
python -m pip install --upgrade pip
```

Installer les dépendances :

```powershell
pip install -r requirements.txt
```

Installer le modèle spaCy :

```powershell
python -m spacy download fr_core_news_md
```

---

## 6.3 Problème d'activation PowerShell

Si PowerShell refuse l'activation :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Puis :

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 6.4 Installer le frontend

Depuis la racine du projet :

```powershell
cd frontend
npm.cmd install
```

---

# 7. Configuration des jetons

## Important

**Ne jamais mettre un vrai jeton directement dans le code ou dans Git.**

Les valeurs présentées ci-dessous sont uniquement des placeholders.

---

## Jeton administrateur

Choisir un jeton :

```powershell
$env:ESIC_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
```

Par exemple, générer une valeur aléatoire avec Python :

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copier ensuite la valeur obtenue :

```powershell
$env:ESIC_ADMIN_TOKEN="COLLER_ICI_LE_JETON_GENERE"
```

Ne jamais écrire cette vraie valeur dans le README Git.

---

## Jeton administrateur des bornes

```powershell
$env:KIOSK_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
```

Pour la démonstration locale, il est possible d'utiliser la même valeur :

```powershell
$env:ESIC_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
$env:KIOSK_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
```

Le jeton saisi dans l'interface Administration doit correspondre au jeton configuré côté backend.

---

## Hugging Face

Le téléchargement du modèle Sentence-Transformers peut fonctionner sans authentification.

Un token Hugging Face est donc facultatif.

Si nécessaire :

```powershell
$env:HF_TOKEN="CHOISIR_UN_JETON_HUGGING_FACE"
```

Ne jamais publier la vraie valeur.

---

## Variables CPU

Pour limiter la sur-parallélisation des bibliothèques ML :

```powershell
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"
$env:TOKENIZERS_PARALLELISM="false"
```

Ces variables sont particulièrement importantes lors des tests de charge.

---

# 8. Installation NLP

Depuis :

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

Installer spaCy :

```powershell
python -m spacy download fr_core_news_md
```

Entraîner les modèles du projet :

```powershell
python scripts/train_nlp_models.py
```

Le dataset utilisé est :

```text
data/nlp_training.csv
```

Les modèles générés sont enregistrés dans :

```text
models/nlp/
```

avec notamment :

```text
category_model.joblib
intent_model.joblib
labels.json
```

---

# 9. Recherche sémantique Sentence-BERT + FAISS

Construire l'index :

```powershell
python scripts/build_semantic_index.py
```

Le modèle utilisé est :

```text
paraphrase-multilingual-MiniLM-L12-v2
```

Les fichiers générés sont notamment :

```text
models/semantic_search/esic_knowledge.faiss
models/semantic_search/esic_knowledge_documents.json
```

Le premier lancement peut télécharger le modèle Sentence-Transformers et prendre plus de temps.

---

## Seuils de recherche

Le système utilise notamment les seuils suivants :

```text
score >= 0.70
    résultat sémantique fort

0.50 <= score < 0.70
    résultat intermédiaire
    décision avec le moteur hybride

score < 0.50
    résultat sémantique insuffisant seul
```

La recherche sémantique est combinée avec la recherche lexicale et les autres signaux disponibles afin de sélectionner le résultat final.

---

# 10. Traduction français / anglais

L'application prend en charge :

```text
Français
English
```

Le pipeline anglais fonctionne selon le principe suivant :

```text
Question anglaise
        │
        ▼
Traduction EN -> FR
        │
        ▼
Moteur de réponse
        │
        ▼
Réponse française
        │
        ▼
Traduction FR -> EN
        │
        ▼
Réponse anglaise
```

---

## Installer Argos Translate

Depuis le backend :

```powershell
python -m pip install argostranslate
```

Puis :

```powershell
python scripts/install_translation_models.py
```

Le script installe les modèles :

```text
en -> fr
fr -> en
```

La traduction locale permet de réduire la dépendance à un service de traduction externe pendant une démonstration.

---

# 11. Lancement du projet

Deux terminaux sont nécessaires.

---

## Terminal 1 — Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

$env:ESIC_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
$env:KIOSK_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"

$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"
$env:TOKENIZERS_PARALLELISM="false"

python -m uvicorn app.main:app --reload
```

Attendre :

```text
Application startup complete.
```

Backend :

```text
127.0.0.1:8000
```

Swagger :

```text
127.0.0.1:8000/docs
```

Health check :

```text
127.0.0.1:8000/health
```

Réponse attendue :

```json
{
  "status": "ok"
}
```

---

## Terminal 2 — Frontend

```powershell
cd frontend
npm.cmd run dev
```

L'application est ensuite accessible sur :

```text
localhost:5173
```

---

# 12. Fonctionnement du chatbot

Le traitement général d'une question suit le pipeline :

```text
Utilisateur
    │
    ▼
Frontend React
    │
    ▼
POST /api/chat
    │
    ▼
Validation conversation
    │
    ▼
Rate limiting
    │
    ▼
Contrôle sécurité
    │
    ▼
Logging
    │
    ▼
Traitement de la question
    │
    ▼
Recherche rapide
    │
    ├── règles
    └── recherche lexicale
    │
    ▼
Résultat suffisamment fiable ?
    │
    ├── OUI ──────────────► réponse
    │
    └── NON
         │
         ▼
   Recherche sémantique
         │
         ▼
 Sentence-BERT + FAISS
         │
         ▼
    Reranking hybride
         │
         ▼
       Réponse
         │
         ▼
 Historique / Analytics
```

---

# 13. Base de connaissances

La base comprend notamment :

```text
faq_complete.json
procedures_esic.json
annuaire_contacts.json
emploi_du_temps.json
emploi_du_temps_exclusive.csv
```

D'autres documents du projet peuvent également être indexés.

Le chatbot doit privilégier les informations présentes dans la base de connaissances.

Lorsqu'aucune information suffisamment fiable n'est disponible, le système doit éviter de fabriquer une réponse institutionnelle.

---

# 14. Administration

L'administration permet notamment de gérer :

```text
Feedbacks
Connaissances
Corrections
Demandes d'assistance
Monitoring des bornes
```

Avant de démarrer le backend :

```powershell
$env:ESIC_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
$env:KIOSK_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
```

Dans l'application :

```text
Administration
      │
      ▼
Saisir le jeton administrateur
      │
      ▼
Accès aux fonctions protégées
```

Ne jamais stocker le vrai jeton dans le repository.

---

# 15. Dashboard

Le dashboard exploite les interactions enregistrées afin de produire différentes statistiques.

Routes principales :

```text
GET /api/dashboard/top-questions
GET /api/dashboard/categories
GET /api/dashboard/evolution
GET /api/dashboard/tendances
```

Exemples :

```text
/api/dashboard/top-questions?limite=10

/api/dashboard/evolution?jours=14
```

Les informations permettent notamment d'analyser :

- les questions fréquentes ;
- la répartition par catégorie ;
- l'évolution du nombre de questions ;
- les tendances.

---

# 16. Mode borne

Le mode borne fournit une interface simplifiée destinée à une utilisation sur un écran interactif.

Il propose notamment des accès rapides à :

```text
Bibliothèque
Formations
Contacts
Vie du campus
```

---

## Saisie vocale

Le mode vocal utilise les fonctions de reconnaissance vocale disponibles dans le navigateur.

Navigateurs recommandés :

```text
Google Chrome
Microsoft Edge
```

L'utilisateur doit autoriser l'accès au microphone.

---

## Journalisation borne

Les interactions de la borne peuvent enregistrer différents événements, par exemple :

```text
kiosk_mode_entered
kiosk_mode_exited
kiosk_category_selected
voice_listening_started
voice_listening_stopped
voice_transcription
question_submitted
assistant_response_received
```

---

## Heartbeat

La borne communique périodiquement son état :

```text
POST /api/kiosk/heartbeat
```

L'administration peut consulter l'état des bornes :

```text
GET /api/kiosk/status
```

Le monitoring est protégé par le jeton administrateur de borne.

---

# 17. Sécurité

Le traitement d'une requête suit notamment :

```text
Requête
   │
   ▼
Rate limiting
   │
   ▼
Contrôle sécurité
   │
   ▼
Logging
   │
   ▼
Traitement
```

Le projet comporte notamment des mécanismes destinés à tester ou limiter :

- les tentatives de prompt injection ;
- certaines entrées XSS ;
- les requêtes excessives ;
- les entrées utilisateur incorrectes ;
- les accès aux fonctions administratives.

Les événements de sécurité peuvent être journalisés.

> Cette sécurité correspond à un prototype pédagogique. Elle ne remplace pas un audit de sécurité pour un déploiement réel.

---

# 18. Tests

Tous les tests backend sont lancés depuis :

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

---

## Test NLP

```powershell
python tests/test_nlp.py
```

---

## Test NLP + base de connaissances

```powershell
python tests/test_nlp_kb.py
```

Ce test vérifie le flux :

```text
Question
   ↓
Traitement
   ↓
Base de connaissances
   ↓
Réponse
```

---

## Test Sentence-BERT + FAISS

```powershell
python tests/test_semantic_search.py
```

Si l'index n'existe pas encore :

```powershell
python scripts/build_semantic_index.py
python tests/test_semantic_search.py
```

---

## Tests de sécurité

```powershell
python tests/test_security.py
```

Ces tests permettent notamment de vérifier les protections prévues contre les entrées malveillantes et le rate limiting.

---

# 19. Tests de performance

## Important

Pour un benchmark, ne pas utiliser :

```text
--reload
```

Arrêter d'abord le serveur de développement :

```text
Ctrl + C
```

Puis lancer :

```powershell
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"
$env:TOKENIZERS_PARALLELISM="false"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Attendre :

```text
Application startup complete.
```

---

## Test standard — 20 utilisateurs

Dans un autre terminal :

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

python tests/test_performance.py
```

Le cahier des charges fixe comme objectif de référence :

```text
20 utilisateurs simultanés
temps de réponse cible < 2 secondes
```

Il s'agit d'un **objectif d'acceptation**, pas d'une garantie de performance sur toutes les machines.

---

## Stress test — 100 utilisateurs

Après le test standard :

```powershell
python tests/test_performance.py --full
```

Le test à 100 utilisateurs sert à observer le comportement du système sous une charge plus importante.

---

# 20. API

La documentation interactive de l'API est disponible via :

```text
127.0.0.1:8000/docs
```

Routes principales du projet :

```text
GET     /health

POST    /api/conversations
GET     /api/conversations
GET     /api/conversations/{conversation_id}

GET     /api/history/{conversation_id}

POST    /api/chat

POST    /api/feedback
GET     /api/feedback/statistics

POST    /api/corrections

POST    /api/escalations

GET     /api/admin/knowledge
POST    /api/admin/knowledge

GET     /api/admin/corrections
PATCH   /api/admin/corrections/{id}

GET     /api/admin/escalations
PATCH   /api/admin/escalations/{id}

POST    /api/kiosk/interactions
GET     /api/kiosk/interactions

POST    /api/kiosk/heartbeat
GET     /api/kiosk/status
GET     /api/kiosk/health

GET     /api/dashboard/top-questions
GET     /api/dashboard/categories
GET     /api/dashboard/evolution
GET     /api/dashboard/tendances
```

La documentation Swagger doit être utilisée pour consulter la liste exacte des routes disponibles dans la version courante du backend.

---

# 21. Git

## Vérifier la configuration

```powershell
git --version
git status
git branch
```

---

## Cas 1 — Le repository Git existe déjà

Cloner :

```powershell
git clone "URL_DU_REPOSITORY"
```

Entrer dans le projet :

```powershell
cd assistant_virtuel_educatif
```

Vérifier les branches :

```powershell
git branch
```

Récupérer les dernières modifications :

```powershell
git pull
```

---

## Créer une branche

```powershell
git checkout -b "NOM_DE_LA_BRANCHE"
```

Exemple :

```powershell
git checkout -b feature/readme
```

---

## Voir les modifications

```powershell
git status
```

---

## Ajouter les fichiers

Pour tout ajouter :

```powershell
git add .
```

Ou uniquement le README :

```powershell
git add README.md
```

---

## Commit

```powershell
git commit -m "docs: complete project README"
```

Autres exemples :

```powershell
git commit -m "feat: add kiosk mode"
git commit -m "feat: add semantic search"
git commit -m "fix: fix english translation"
git commit -m "test: add security tests"
git commit -m "test: add performance tests"
git commit -m "docs: update installation guide"
```

---

## Premier push d'une branche

```powershell
git push -u origin "NOM_DE_LA_BRANCHE"
```

Exemple :

```powershell
git push -u origin feature/readme
```

---

## Push suivant

```powershell
git push
```

---

## Mettre à jour sa branche

```powershell
git pull
```

Ou explicitement :

```powershell
git pull origin "NOM_DE_LA_BRANCHE"
```

---

## Cas 2 — Projet local pas encore connecté à Git

Depuis la racine :

```powershell
git init
```

Ajouter les fichiers :

```powershell
git add .
```

Premier commit :

```powershell
git commit -m "Initial commit"
```

Nommer la branche principale :

```powershell
git branch -M main
```

Ajouter le repository distant :

```powershell
git remote add origin "URL_DU_REPOSITORY"
```

Vérifier :

```powershell
git remote -v
```

Envoyer le projet :

```powershell
git push -u origin main
```

---

# 22. `.gitignore`

Le projet doit au minimum ignorer :

```gitignore
# ============================================================
# PYTHON
# ============================================================

__pycache__/
*.py[cod]
*.pyo

.pytest_cache/

.venv/
venv/

# ============================================================
# NODE / VITE
# ============================================================

node_modules/
frontend/node_modules/
frontend/dist/

# ============================================================
# SECRETS
# ============================================================

.env
.env.*
!.env.example

# ============================================================
# BASES SQLITE LOCALES
# ============================================================

*.db
*.sqlite
*.sqlite3
*.db-wal
*.db-shm

# ============================================================
# LOGS
# ============================================================

*.log

# ============================================================
# CACHE
# ============================================================

.cache/

# ============================================================
# IDE
# ============================================================

.vscode/
.idea/

# ============================================================
# OS
# ============================================================

.DS_Store
Thumbs.db
```

---

## Secrets à ne jamais committer

Ne jamais envoyer sur Git :

```text
ESIC_ADMIN_TOKEN réel
KIOSK_ADMIN_TOKEN réel
HF_TOKEN réel
mot de passe
clé API
token d'accès
secret d'authentification
```

Le README doit contenir uniquement des placeholders :

```text
"CHOISIR_UN_JETON_ADMIN"
"CHOISIR_UN_JETON_HUGGING_FACE"
"URL_DU_REPOSITORY"
"NOM_DE_LA_BRANCHE"
```

---

# 23. Dépannage

## `ModuleNotFoundError`

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Modèles NLP absents

Si les modèles sont introuvables :

```powershell
python scripts/train_nlp_models.py
```

---

## `fr_core_news_md` absent

```powershell
python -m spacy download fr_core_news_md
```

---

## Index FAISS absent

```powershell
python scripts/build_semantic_index.py
```

Puis :

```powershell
python tests/test_semantic_search.py
```

---

## Traduction anglaise indisponible

```powershell
python -m pip install argostranslate
python scripts/install_translation_models.py
```

Puis redémarrer le backend.

---

## Administration inaccessible

Vérifier :

```powershell
$env:ESIC_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
$env:KIOSK_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
```

Les variables doivent être définies **avant de lancer Uvicorn**.

Après modification :

```text
Ctrl + C
```

puis relancer le backend.

---

## Frontend inaccessible

Vérifier que Vite fonctionne :

```powershell
cd frontend
npm.cmd run dev
```

Puis ouvrir :

```text
localhost:5173
```

---

## Backend inaccessible

Vérifier :

```text
127.0.0.1:8000/health
```

Puis consulter :

```text
127.0.0.1:8000/docs
```

---

## Microphone inaccessible

Utiliser de préférence :

```text
Chrome
Edge
```

et autoriser l'accès au microphone dans le navigateur.

---

## Premier démarrage lent

Le premier lancement peut nécessiter le chargement des modèles.

Attendre :

```text
Application startup complete.
```

avant de tester l'application.

---

# 24. Démarrage rapide

## Première installation du backend

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

python -m spacy download fr_core_news_md

python scripts/train_nlp_models.py
python scripts/build_semantic_index.py
python scripts/install_translation_models.py
```

---

## Démarrer le backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

$env:ESIC_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"
$env:KIOSK_ADMIN_TOKEN="CHOISIR_UN_JETON_ADMIN"

$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"
$env:TOKENIZERS_PARALLELISM="false"

python -m uvicorn app.main:app --reload
```

---

## Démarrer le frontend

Dans un deuxième terminal :

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Puis ouvrir :

```text
localhost:5173
```

---

# 25. Commandes de test — résumé

Backend lancé dans un terminal.

Dans un autre terminal :

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

python tests/test_nlp.py
python tests/test_nlp_kb.py
python tests/test_semantic_search.py
python tests/test_security.py
```

Pour les performances, redémarrer d'abord Uvicorn **sans `--reload`** :

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Puis :

```powershell
python tests/test_performance.py
```

Stress test :

```powershell
python tests/test_performance.py --full
```

---

# 26. Commandes Git — résumé final

Pour envoyer le README :

```powershell
git status

git add README.md

git commit -m "docs: complete project README"

git push
```

Pour envoyer toutes les modifications du projet :

```powershell
git status

git add .

git commit -m "feat: finalize ESIC Assistant"

git push
```

Avant un nouveau travail en équipe :

```powershell
git pull
```

---

# Équipe

Projet transverse réalisé dans le cadre de :

**ESIC — ESIS-2 / CPDIA-2**

Le projet est organisé selon une méthodologie Scrum avec gestion des fonctionnalités sous forme de User Stories.

---

# Avertissement

ESIC Assistant est un **prototype pédagogique**.

Une mise en production institutionnelle nécessiterait notamment :

- une authentification institutionnelle réelle ;
- une gestion sécurisée et centralisée des secrets ;
- une revue de sécurité ;
- une politique RGPD complète ;
- une politique de conservation des données ;
- un chiffrement adapté ;
- une infrastructure de production ;
- des sauvegardes ;
- du monitoring ;
- de l'alerting ;
- des tests de charge supplémentaires ;
- un audit de sécurité.