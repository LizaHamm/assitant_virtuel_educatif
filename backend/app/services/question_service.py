def process_question(message: str) -> str:
    """Nettoie la question avant le pipeline NLP / base de connaissances.

    La classification NLP est volontairement réalisée dans ``app.main`` afin
    qu'une seule analyse soit réutilisée pour le routage documentaire, les
    entités, la clarification et les métadonnées renvoyées au frontend.
    """
    question = " ".join(message.strip().split())

    if not question:
        raise ValueError("La question ne peut pas être vide.")

    return question
