# Architecture MVP

```text
Utilisateur
    |
    v
React / Vite
    |
    | HTTP POST /api/chat
    v
FastAPI
    |
    +--> traitement de la question
    |
    +--> génération de réponse temporaire
    |
    v
Réponse JSON
    |
    v
React
```

La base de connaissances et les composants NLP seront intégrés progressivement.
