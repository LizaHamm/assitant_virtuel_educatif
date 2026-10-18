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
    build_semantic_index,
)


if __name__ == "__main__":

    print(
        "Construction de l'index "
        "sémantique ESIC..."
    )

    result = build_semantic_index()

    print(
        "\n=============================="
    )

    print(
        "INDEX FAISS CRÉÉ"
    )

    print(
        "=============================="
    )

    print(
        "Documents :",
        result["documents"],
    )

    print(
        "Dimension :",
        result["dimension"],
    )

    print(
        "Index :",
        result["index_path"],
    )

    print(
        "Métadonnées :",
        result["documents_path"],
    )