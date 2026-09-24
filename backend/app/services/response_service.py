def generate_response(question: str) -> str:
    """
    Génération de réponse temporaire pour le MVP.
    Les vrais datasets fournis par le professeur seront intégrés plus tard.
    """
    normalized = question.lower()

    if any(word in normalized for word in ["bonjour", "salut", "hello"]):
        return "Bonjour ! Comment puis-je vous aider ?"

    if "bibliothèque" in normalized or "bibliotheque" in normalized:
        return (
            "Je pourrai vous renseigner sur la bibliothèque lorsque les "
            "datasets officiels du projet seront intégrés."
        )

    return (
        "J'ai bien reçu votre question. La base de connaissances officielle "
        "sera intégrée dès que les datasets du projet seront disponibles."
    )
