from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.nlp_services import analyze_question
from app.services.response_service import generate_response, search_esic_knowledge

QUESTIONS = [
    "Quels sont les prérequis pour intégrer le Master IA ?",
    "Quels métiers peut-on faire après le Master IA ?",
    "Quelles pièces faut-il fournir pour une convention de stage ?",
    "Comment emprunter un livre à la bibliothèque ?",
    "Qui contacter pour prendre rendez-vous avec la scolarité ?",
    "Que dit le règlement sur la fraude pendant un examen ?",
    "Quand sont les rattrapages ?",
]

FORBIDDEN_DUMP_MARKERS = (
    "nombre_total_questions",
    "langues_disponibles",
    "metadata : titre",
    "document créé exclusivement pour le projet étudiant etablissement",
)


def main():
    print("=" * 90)
    print("TEST INTÉGRATION NLP -> BASE DE CONNAISSANCES -> RÉPONSE")
    print("=" * 90)

    for i, question in enumerate(QUESTIONS, 1):
        nlp = analyze_question(question)
        results = search_esic_knowledge(question, nlp_result=nlp, limit=3)
        answer = generate_response(question, nlp_result=nlp)

        print(f"\n[{i}] {question}")
        print(f"Catégorie : {nlp['category']} ({nlp['category_confidence']:.1%})")
        print(f"Intention : {nlp['intent']} ({nlp['intent_confidence']:.1%})")
        print(f"Entités   : {nlp['entities']}")
        print("Candidats :")
        if results:
            for result in results:
                record = result.get("record") or {}
                label = (
                    record.get("question")
                    or record.get("titre")
                    or record.get("nom")
                    or "entrée ESIC"
                )
                print(
                    f"  - {result.get('source')} | score={result.get('score'):.3f} | {label}"
                )
        else:
            print("  - aucun")

        print("Réponse :")
        print(answer)

        normalized_answer = answer.casefold()
        if len(answer) > 5000:
            print("ERREUR : réponse anormalement longue (> 5000 caractères)")
        elif any(marker in normalized_answer for marker in FORBIDDEN_DUMP_MARKERS):
            print("ERREUR : un document brut semble encore être exposé")
        else:
            print("OK : pas de dump massif détecté")


if __name__ == "__main__":
    main()
