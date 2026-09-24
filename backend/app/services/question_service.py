def process_question(message: str) -> str:
    """
    Prépare la question avant le traitement de la réponse.
    Pour le MVP, on fait uniquement une validation/nettoyage simple.
    La classification NLP sera ajoutée dans une étape ultérieure.
    """
    question = " ".join(message.strip().split())

    if not question:
        raise ValueError("La question ne peut pas être vide.")

    return question
