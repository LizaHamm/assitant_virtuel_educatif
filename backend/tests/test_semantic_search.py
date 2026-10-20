from pathlib import Path
import sys


BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIR),
    )


from app.services.semantic_search_service import (
    semantic_search,
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

    print(
        "\n=============================="
    )

    print(
        "TEST SENTENCE-BERT + FAISS"
    )

    print(
        "=============================="
    )

    for question in QUESTIONS:

        print(
            "\n\nQUESTION :",
            question,
        )

        results = semantic_search(
            question,
            top_k=3,
        )

        if not results:

            print(
                "AUCUN RÉSULTAT"
            )

            continue

        for position, result in enumerate(
            results,
            start=1,
        ):

            print(
                f"\n#{position}"
            )

            print(
                "Score :",
                result["score"],
            )

            print(
                "Confiance :",
                result["confidence"],
            )

            print(
                "Accepté >= 0.70 :",
                result["accepted"],
            )

            print(
                "Source :",
                result["source"],
            )

            print(
                "Label :",
                result["label"],
            )

            print(
                "Texte :",
                result["text"][:500],
            )


if __name__ == "__main__":
    main()