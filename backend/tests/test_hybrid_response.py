from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.nlp_services import analyze_question
from app.services.response_service import (
    generate_response,
    search_esic_knowledge,
)

QUESTIONS = [
    "Quels sont les prérequis pour intégrer le Master IA ?",
    "Comment obtenir une convention de stage ?",
    "Quels documents faut-il fournir pour une convention de stage ?",
    "Comment contacter la scolarité ?",
    "Quels sont les horaires de la bibliothèque ?",
    "Quelles sont les sanctions en cas de fraude ?",
    "Comment me connecter au Wi-Fi du campus ?",
    "Quels métiers peut-on faire après une formation en Data Science ?",
    "Quand ont lieu les rattrapages ?",
    "Comment emprunter un livre à la bibliothèque ?",
]


def main():
    print("=" * 90)
    print("TEST CHATBOT HYBRIDE — NLP + 15 INTENTIONS + LEXICAL + SBERT/FAISS")
    print("=" * 90)

    for question in QUESTIONS:
        print("\n" + "-" * 90)
        print("QUESTION :", question)

        nlp_result = analyze_question(question)
        print("NLP catégorie :", nlp_result.get("category"), nlp_result.get("category_confidence"))
        print("NLP intention :", nlp_result.get("intent"), nlp_result.get("intent_confidence"))
        print("Entités :", nlp_result.get("entities"))

        results = search_esic_knowledge(question, nlp_result=nlp_result, limit=3)
        print("\nTOP HYBRIDE :")
        for index, item in enumerate(results, start=1):
            print(
                f"#{index} hybrid={item.get('hybrid_score', item.get('score'))} "
                f"semantic={item.get('semantic_score')} "
                f"lexical={item.get('lexical_score')} "
                f"via={item.get('retrieval')} "
                f"source={item.get('source')}"
            )
            record = item.get("record") or {}
            label = (
                record.get("question")
                or record.get("titre")
                or record.get("nom")
                or item.get("label")
                or ""
            ) if isinstance(record, dict) else str(record)[:120]
            print("   label :", label)

        answer = generate_response(question, nlp_result=nlp_result)
        print("\nRÉPONSE CHATBOT :")
        print(answer)

        lowered = answer.casefold()
        forbidden = (
            "nombre_total_questions",
            "langues_disponibles",
            "document créé exclusivement pour le projet étudiant joel banka titre",
        )
        if len(answer) > 5000 or any(marker in lowered for marker in forbidden):
            print("[ERREUR] La réponse ressemble encore à un dump de la base.")


if __name__ == "__main__":
    main()
