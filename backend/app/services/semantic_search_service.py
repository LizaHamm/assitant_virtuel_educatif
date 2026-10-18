from __future__ import annotations

import csv
import io
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# CHEMINS DU PROJET
# ============================================================

# Fichier :
# backend/app/services/semantic_search_service.py
#
# parents[0] = services
# parents[1] = app
# parents[2] = backend
# parents[3] = racine du projet

PROJECT_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_DIR / "data"

SEMANTIC_DIR = (
    PROJECT_DIR
    / "models"
    / "semantic_search"
)

SEMANTIC_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

INDEX_PATH = (
    SEMANTIC_DIR
    / "esic_knowledge.faiss"
)

DOCUMENTS_PATH = (
    SEMANTIC_DIR
    / "esic_knowledge_documents.json"
)


# ============================================================
# CONFIGURATION SENTENCE-BERT / FAISS
# ============================================================

MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

# Cahier des charges :
#
# score >= 0.70 :
# résultat considéré comme suffisamment fiable.
#
# 0.50 <= score < 0.70 :
# résultat moyen, qui pourra ensuite être combiné
# avec le NLP et la recherche lexicale.
#
# score < 0.50 :
# résultat trop faible.

ACCEPTED_THRESHOLD = 0.70

LOW_THRESHOLD = 0.50

DEFAULT_TOP_K = 5


# ============================================================
# SOURCES DE CONNAISSANCES
# ============================================================

JSON_FILES = [

    DATA_DIR
    / "faq_complete.json",

    DATA_DIR
    / "procedures_esic.json",

    DATA_DIR
    / "annuaire_contacts.json",

    DATA_DIR
    / "emploi_du_temps.json",
]


CSV_FILES = [

    DATA_DIR
    / "emploi_du_temps_exclusive.csv",
]


PDF_FILES = [

    DATA_DIR
    / (
        "Guide de l etudiant Projet "
        "Assistant Virtuel Educatif exclusif.pdf"
    ),

    DATA_DIR
    / (
        "PROCÉDURES ADMINISTRATIVES "
        "ET ACADÉMIQUES ESIC.pdf"
    ),

    DATA_DIR
    / (
        "Règlement Intérieur Projet "
        "Assistant Virtuel Campus.pdf"
    ),

    DATA_DIR
    / (
        "Les données utiles pour le projet "
        "Assistant virtuel campus.pdf"
    ),
]


# ============================================================
# MODÈLE SENTENCE-BERT
# ============================================================

@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Charge Sentence-BERT une seule fois.

    Le cache évite de recharger le modèle
    pour chaque question.
    """

    logger.info(
        "Chargement du modèle Sentence-BERT : %s",
        MODEL_NAME,
    )

    return SentenceTransformer(
        MODEL_NAME
    )


# ============================================================
# OUTILS TEXTE
# ============================================================

def clean_text(
    value: Any,
) -> str:
    """
    Transforme une valeur quelconque
    en texte propre.
    """

    if value is None:
        return ""

    text = str(value)

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def useful_scalar(
    value: Any,
) -> bool:
    """
    Indique si la valeur peut être
    directement transformée en texte.
    """

    return isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    )


def flatten_value(
    value: Any,
    prefix: str = "",
) -> list[str]:
    """
    Transforme récursivement un dictionnaire
    ou une liste en petites chaînes lisibles.
    """

    parts: list[str] = []

    if useful_scalar(value):

        text = clean_text(
            value
        )

        if text:

            if prefix:

                parts.append(
                    f"{prefix}: {text}"
                )

            else:

                parts.append(
                    text
                )

        return parts

    if isinstance(
        value,
        list,
    ):

        for item in value:

            parts.extend(
                flatten_value(
                    item,
                    prefix,
                )
            )

        return parts

    if isinstance(
        value,
        dict,
    ):

        for key, item in value.items():

            normalized_key = (
                str(key)
                .replace("_", " ")
                .strip()
            )

            parts.extend(
                flatten_value(
                    item,
                    normalized_key,
                )
            )

    return parts


# ============================================================
# MÉTADONNÉES À NE PAS INDEXER
# ============================================================

IGNORED_METADATA_KEYS = {

    "metadata",
    "meta",

    "auteur",
    "author",

    "purpose",
    "version",

    "nombre_total_questions",
    "nombre questions",

    "langues_disponibles",
    "langues disponibles",

    "date_creation",
    "date création",
}


# ============================================================
# DÉTECTION DES ENREGISTREMENTS ATOMIQUES
# ============================================================

def looks_atomic(
    record: dict,
) -> bool:
    """
    Détermine si un dictionnaire correspond
    à une vraie unité de connaissance.

    On veut par exemple :

    - une question/réponse FAQ
    - une procédure
    - une étape de procédure
    - un contact
    - un créneau d'emploi du temps

    On ne veut PAS :

    - toute la FAQ
    - toute une catégorie FAQ
    - tout le JSON
    - les métadonnées
    """

    keys = {
        str(key).casefold()
        for key in record.keys()
    }

    # --------------------------------------------------------
    # FAQ individuelle
    # --------------------------------------------------------

    if (
        "question" in keys
        and (
            "reponse" in keys
            or "réponse" in keys
            or "answer" in keys
        )
    ):

        return True

    # --------------------------------------------------------
    # Contact
    # --------------------------------------------------------

    if (
        "email" in keys
        or "telephone" in keys
        or "téléphone" in keys
    ):

        return True

    # --------------------------------------------------------
    # Procédure / étape
    # --------------------------------------------------------

    if (
        "titre" in keys
        or "title" in keys
    ) and (
        "description" in keys
        or "prerequis" in keys
        or "prérequis" in keys
        or "documents_necessaires" in keys
        or "documents nécessaires" in keys
        or "etapes" in keys
        or "étapes" in keys
        or "conseils" in keys
    ):

        return True

    # --------------------------------------------------------
    # Créneau d'emploi du temps
    # --------------------------------------------------------

    has_formation = (
        "formation" in keys
        or "groupe" in keys
    )

    has_day = (
        "jour" in keys
        or "date" in keys
    )

    has_time = (
        "heure" in keys
        or "horaire" in keys
        or "heure_debut" in keys
        or "heure_fin" in keys
        or "heure début" in keys
        or "heure fin" in keys
    )

    if (
        has_formation
        and has_day
        and has_time
    ):

        return True

    return False


# ============================================================
# CONSTRUCTION D'UN DOCUMENT SÉMANTIQUE
# ============================================================

def record_to_document(
    record: dict,
    source: str,
) -> dict | None:
    """
    Transforme une entrée JSON en document FAISS.

    IMPORTANT :

    search_text :
        texte court utilisé pour Sentence-BERT.

    text :
        contenu complet conservé pour produire
        ensuite la réponse utilisateur.

    Cela évite de comparer une petite question
    utilisateur avec plusieurs milliers de
    caractères de JSON.
    """

    filtered = {

        key: value

        for key, value
        in record.items()

        if str(key).casefold()
        not in IGNORED_METADATA_KEYS
    }

    parts = flatten_value(
        filtered
    )

    full_text = clean_text(
        " | ".join(
            parts
        )
    )

    if len(full_text) < 15:

        return None

    # Protection contre les énormes dumps.
    full_text = full_text[:4000]

    question = clean_text(
        record.get(
            "question",
            "",
        )
    )

    title = clean_text(
        record.get(
            "titre",
            record.get(
                "title",
                "",
            ),
        )
    )

    description = clean_text(
        record.get(
            "description",
            "",
        )
    )

    category = clean_text(
        record.get(
            "categorie",
            record.get(
                "category",
                "",
            ),
        )
    )

    tags_value = record.get(
        "tags",
        [],
    )

    if isinstance(
        tags_value,
        list,
    ):

        tags = " ".join(

            clean_text(tag)

            for tag
            in tags_value

            if clean_text(tag)
        )

    else:

        tags = clean_text(
            tags_value
        )

    keys = {
        str(key).casefold()
        for key in record.keys()
    }

    # ========================================================
    # FAQ
    # ========================================================

    if question:

        search_parts = [
            question,
            tags,
            category,
        ]

        document_type = (
            "faq"
        )

        label = question

    # ========================================================
    # CONTACT
    #
    # ATTENTION :
    # ce bloc doit être AVANT le bloc procédure,
    # car les contacts peuvent avoir un champ "titre"
    # contenant par exemple "Dr.".
    # ========================================================

    elif (
        "email" in keys
        or "telephone" in keys
        or "téléphone" in keys
    ):

        service = clean_text(
            record.get(
                "service",
                "",
            )
        )

        formation = clean_text(
            record.get(
                "formation",
                "",
            )
        )

        nom = clean_text(
            record.get(
                "nom",
                "",
            )
        )

        prenom = clean_text(
            record.get(
                "prenom",
                record.get(
                    "prénom",
                    "",
                ),
            )
        )

        fonction = clean_text(
            record.get(
                "fonction",
                record.get(
                    "poste",
                    "",
                ),
            )
        )

        search_parts = [

            "contact coordonnées "
            "email téléphone joindre",

            service,

            formation,

            fonction,

            nom,

            prenom,
        ]

        document_type = (
            "contact"
        )

        label_parts = [

            service,
            formation,
            fonction,

            " ".join(
                part
                for part in [
                    prenom,
                    nom,
                ]
                if part
            ),
        ]

        label = " - ".join(
            part
            for part in label_parts
            if part
        )

        if not label:

            label = (
                full_text[:100]
            )

    # ========================================================
    # PROCÉDURE / ÉTAPE
    # ========================================================

    elif title:

        search_parts = [
            title,
            description,
            category,
        ]

        if (
            record.get(
                "prerequis"
            )
            or record.get(
                "prérequis"
            )
        ):

            search_parts.append(
                "prérequis conditions "
                "conditions nécessaires "
                "conditions admission"
            )

        if (
            record.get(
                "documents_necessaires"
            )
            or record.get(
                "documents nécessaires"
            )
        ):

            search_parts.append(
                "documents nécessaires "
                "documents à fournir "
                "pièces à fournir "
                "justificatifs nécessaires"
            )

        if (
            record.get(
                "etapes"
            )
            or record.get(
                "étapes"
            )
        ):

            search_parts.append(
                "procédure étapes "
                "démarche comment faire"
            )

        if record.get(
            "conseils"
        ):

            search_parts.append(
                "conseils informations "
                "procédure"
            )

        public_concerne = clean_text(
            record.get(
                "public_concerne",
                "",
            )
        )

        periode = clean_text(
            record.get(
                "periode",
                "",
            )
        )

        if public_concerne:

            search_parts.append(
                public_concerne
            )

        if periode:

            search_parts.append(
                periode
            )

        document_type = (
            "procedure"
        )

        label = title

    # ========================================================
    # PLANNING
    # ========================================================

    elif (
        (
            "formation" in keys
            or "groupe" in keys
        )
        and (
            "jour" in keys
            or "date" in keys
        )
    ):

        formation = clean_text(
            record.get(
                "formation",
                "",
            )
        )

        groupe = clean_text(
            record.get(
                "groupe",
                "",
            )
        )

        jour = clean_text(
            record.get(
                "jour",
                "",
            )
        )

        date = clean_text(
            record.get(
                "date",
                "",
            )
        )

        cours = clean_text(
            record.get(
                "cours",
                record.get(
                    "matiere",
                    record.get(
                        "matière",
                        "",
                    ),
                ),
            )
        )

        salle = clean_text(
            record.get(
                "salle",
                "",
            )
        )

        search_parts = [

            "emploi du temps "
            "planning cours horaire",

            formation,
            groupe,
            cours,
            jour,
            date,
            salle,
        ]

        document_type = (
            "planning"
        )

        label = (
            cours
            or formation
            or groupe
            or full_text[:100]
        )

    # ========================================================
    # CONNAISSANCE GÉNÉRIQUE
    # ========================================================

    else:

        search_parts = [
            full_text[:800]
        ]

        document_type = (
            "knowledge"
        )

        label = (
            clean_text(
                record.get(
                    "nom",
                    "",
                )
            )
            or full_text[:100]
        )

    search_text = clean_text(
        " | ".join(

            part

            for part
            in search_parts

            if part
        )
    )

    if not search_text:

        search_text = (
            full_text[:800]
        )

    return {

        "source":
            source,

        "type":
            document_type,

        "label":
            label,

        # Texte utilisé pour créer
        # l'embedding Sentence-BERT.
        "search_text":
            search_text,

        # Texte complet disponible
        # pour construire la réponse.
        "text":
            full_text,

        # Données structurées originales.
        "data":
            filtered,
    }


# ============================================================
# EXTRACTION JSON RÉCURSIVE
# ============================================================

def extract_json_documents(
    value: Any,
    source: str,
) -> list[dict]:
    """
    Parcourt récursivement les JSON.

    Une procédure peut contenir elle-même
    des sous-étapes ou des FAQ.
    """

    documents: list[dict] = []

    if isinstance(
        value,
        list,
    ):

        for item in value:

            documents.extend(
                extract_json_documents(
                    item,
                    source,
                )
            )

        return documents

    if not isinstance(
        value,
        dict,
    ):

        return documents

    # --------------------------------------------------------
    # Ajout de l'entrée actuelle si elle
    # constitue une vraie unité de connaissance.
    # --------------------------------------------------------

    if looks_atomic(
        value
    ):

        document = (
            record_to_document(
                value,
                source,
            )
        )

        if document:

            documents.append(
                document
            )

    # --------------------------------------------------------
    # Recherche dans les enfants.
    # --------------------------------------------------------

    for key, child in value.items():

        normalized_key = (
            str(key).casefold()
        )

        if (
            normalized_key
            in IGNORED_METADATA_KEYS
        ):

            continue

        if isinstance(
            child,
            (
                dict,
                list,
            ),
        ):

            documents.extend(
                extract_json_documents(
                    child,
                    source,
                )
            )

    return documents


# ============================================================
# CHARGEMENT JSON
# ============================================================

def load_json_file(
    path: Path,
) -> list[dict]:

    if not path.exists():

        logger.warning(
            "Fichier JSON absent : %s",
            path,
        )

        return []

    try:

        data = json.loads(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

    except UnicodeDecodeError:

        try:

            data = json.loads(
                path.read_text(
                    encoding="cp1252"
                )
            )

        except Exception as exc:

            logger.error(
                "Impossible de lire %s : %s",
                path.name,
                exc,
            )

            return []

    except Exception as exc:

        logger.error(
            "Impossible de lire %s : %s",
            path.name,
            exc,
        )

        return []

    documents = (
        extract_json_documents(
            data,
            path.name,
        )
    )

    logger.info(
        "%s : %s documents atomiques",
        path.name,
        len(documents),
    )

    return documents


# ============================================================
# CSV — DÉTECTION ENCODAGE
# ============================================================

def read_text_with_fallback(
    path: Path,
) -> tuple[str | None, str | None]:
    """
    Essaie plusieurs encodages.

    Le fichier emploi_du_temps_exclusive.csv
    fourni dans le projet peut être enregistré
    en Windows-1252 / ANSI.
    """

    encodings = [

        "utf-8-sig",

        "utf-8",

        "cp1252",

        "latin-1",
    ]

    for encoding in encodings:

        try:

            content = (
                path.read_text(
                    encoding=encoding,
                )
            )

            return (
                content,
                encoding,
            )

        except UnicodeDecodeError:

            continue

        except OSError as exc:

            logger.error(
                "Erreur de lecture de %s : %s",
                path.name,
                exc,
            )

            return (
                None,
                None,
            )

    return (
        None,
        None,
    )


# ============================================================
# CSV — DÉTECTION DE LA VRAIE LIGNE D'EN-TÊTE
# ============================================================

def detect_csv_header_index(
    lines: list[str],
) -> int:
    """
    Certains CSV ESIC peuvent contenir
    une ligne de métadonnées avant l'en-tête.

    On cherche donc automatiquement
    la première ligne ressemblant
    réellement à un header de planning.
    """

    expected_words = {

        "formation",
        "groupe",

        "jour",
        "date",

        "cours",
        "matiere",
        "matière",

        "heure",
        "horaire",

        "salle",

        "enseignant",
    }

    for index, line in enumerate(
        lines[:25]
    ):

        if ";" not in line:

            continue

        cells = [
            clean_text(cell).casefold()
            for cell in line.split(";")
        ]

        matches = sum(
            1
            for cell in cells
            if any(
                expected in cell
                for expected
                in expected_words
            )
        )

        # Deux noms de colonnes connus suffisent.
        if matches >= 2:

            return index

    # Si aucun header spécial n'est détecté,
    # on utilise la première ligne.
    return 0


# ============================================================
# CSV — CHARGEMENT
# ============================================================

def load_csv_file(
    path: Path,
) -> list[dict]:

    if not path.exists():

        logger.warning(
            "CSV absent : %s",
            path,
        )

        return []

    content, used_encoding = (
        read_text_with_fallback(
            path
        )
    )

    if content is None:

        logger.error(
            "Impossible de décoder %s",
            path.name,
        )

        return []

    logger.info(
        "%s lu avec encodage %s",
        path.name,
        used_encoding,
    )

    lines = [
        line
        for line in content.splitlines()
        if line.strip()
    ]

    if not lines:

        return []

    header_index = (
        detect_csv_header_index(
            lines
        )
    )

    csv_content = "\n".join(
        lines[
            header_index:
        ]
    )

    documents: list[dict] = []

    try:

        reader = csv.DictReader(
            io.StringIO(
                csv_content
            ),
            delimiter=";",
        )

        for row in reader:

            if not row:

                continue

            filtered = {}

            for key, value in row.items():

                if key is None:

                    continue

                key_clean = clean_text(
                    key
                )

                value_clean = clean_text(
                    value
                )

                if (
                    key_clean
                    and value_clean
                ):

                    filtered[
                        key_clean
                    ] = value_clean

            if not filtered:

                continue

            # ------------------------------------------------
            # Ignore les lignes ne contenant
            # pratiquement aucune information.
            # ------------------------------------------------

            meaningful_values = [

                value

                for value
                in filtered.values()

                if value
                and value
                not in {
                    "-",
                    "--",
                    ";",
                }
            ]

            if len(
                meaningful_values
            ) < 2:

                continue

            # ------------------------------------------------
            # Recherche souple des colonnes.
            # ------------------------------------------------

            normalized_columns = {

                key.casefold():
                    value

                for key, value
                in filtered.items()
            }

            def get_column(
                *names: str,
            ) -> str:

                for name in names:

                    target = (
                        name.casefold()
                    )

                    # Correspondance exacte.
                    if (
                        target
                        in normalized_columns
                    ):

                        return clean_text(
                            normalized_columns[
                                target
                            ]
                        )

                    # Correspondance partielle.
                    for key, value in (
                        normalized_columns.items()
                    ):

                        if (
                            target in key
                            or key in target
                        ):

                            return clean_text(
                                value
                            )

                return ""

            formation = get_column(
                "formation"
            )

            groupe = get_column(
                "groupe"
            )

            cours = get_column(
                "cours",
                "matiere",
                "matière",
                "module",
            )

            jour = get_column(
                "jour"
            )

            date = get_column(
                "date"
            )

            horaire = get_column(
                "horaire",
                "heure",
                "heure debut",
                "heure début",
            )

            salle = get_column(
                "salle"
            )

            enseignant = get_column(
                "enseignant",
                "professeur",
                "intervenant",
            )

            full_text = " | ".join(

                f"{key}: {value}"

                for key, value
                in filtered.items()
            )

            search_parts = [

                "emploi du temps "
                "planning cours horaire",

                formation,

                groupe,

                cours,

                jour,

                date,

                horaire,

                salle,

                enseignant,
            ]

            search_text = clean_text(
                " | ".join(

                    value

                    for value
                    in search_parts

                    if value
                )
            )

            label = (
                cours
                or formation
                or groupe
                or full_text[:100]
            )

            documents.append({

                "source":
                    path.name,

                "type":
                    "planning",

                "label":
                    label,

                "search_text":
                    search_text
                    or full_text[:800],

                "text":
                    full_text[:4000],

                "data":
                    filtered,
            })

    except Exception as exc:

        logger.error(
            "Impossible de lire %s : %s",
            path.name,
            exc,
        )

        return []

    logger.info(
        "%s : %s créneaux",
        path.name,
        len(documents),
    )

    return documents


# ============================================================
# PDF — DÉCOUPAGE
# ============================================================

def split_pdf_text(
    text: str,
    max_chars: int = 1200,
) -> list[str]:
    """
    Découpe une page PDF en passages.

    On évite de vectoriser une page entière
    lorsque celle-ci contient plusieurs sujets.
    """

    text = clean_text(
        text
    )

    if not text:

        return []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    chunks: list[str] = []

    current: list[str] = []

    current_length = 0

    for sentence in sentences:

        sentence = clean_text(
            sentence
        )

        if not sentence:

            continue

        if (
            current
            and (
                current_length
                + len(sentence)
                > max_chars
            )
        ):

            chunks.append(
                " ".join(
                    current
                )
            )

            # Petit chevauchement :
            # on conserve la dernière phrase
            # afin de ne pas perdre totalement
            # le contexte entre deux blocs.

            last_sentence = (
                current[-1]
                if current
                else ""
            )

            current = (
                [last_sentence]
                if last_sentence
                else []
            )

            current_length = (
                len(last_sentence)
                if last_sentence
                else 0
            )

        current.append(
            sentence
        )

        current_length += (
            len(sentence)
            + 1
        )

    if current:

        chunks.append(
            " ".join(
                current
            )
        )

    return chunks


# ============================================================
# PDF — CHARGEMENT
# ============================================================

def load_pdf_file(
    path: Path,
) -> list[dict]:

    if not path.exists():

        logger.warning(
            "PDF absent : %s",
            path,
        )

        return []

    documents: list[dict] = []

    previous_page_tail = ""

    try:

        reader = PdfReader(
            str(path)
        )

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):

            page_text = clean_text(
                page.extract_text()
                or ""
            )

            if not page_text:

                continue

            chunks = split_pdf_text(
                page_text
            )

            for chunk_number, chunk in enumerate(
                chunks,
                start=1,
            ):

                semantic_chunk = (
                    chunk
                )

                # Le début d'une nouvelle page peut être
                # la continuation d'une section précédente.
                # On ajoute donc un petit contexte de la
                # page précédente au premier passage.

                if (
                    chunk_number == 1
                    and previous_page_tail
                ):

                    semantic_chunk = clean_text(
                        previous_page_tail
                        + " "
                        + chunk
                    )

                documents.append({

                    "source":
                        path.name,

                    "type":
                        "pdf",

                    "label": (
                        f"{path.stem} - "
                        f"page {page_number}"
                    ),

                    "search_text":
                        semantic_chunk[:1600],

                    "text":
                        chunk[:4000],

                    "data": {

                        "page":
                            page_number,

                        "chunk":
                            chunk_number,
                    },
                })

            # On conserve une petite fin de page
            # pour aider les sections coupées
            # par un changement de page.

            previous_page_tail = (
                page_text[-350:]
            )

    except Exception as exc:

        logger.error(
            "Impossible de lire le PDF %s : %s",
            path.name,
            exc,
        )

        return []

    logger.info(
        "%s : %s passages",
        path.name,
        len(documents),
    )

    return documents


# ============================================================
# CHARGEMENT DU CORPUS COMPLET
# ============================================================

def load_all_documents() -> list[dict]:
    """
    Charge toutes les sources ESIC.

    Retourne uniquement des unités
    de connaissances exploitables.
    """

    documents: list[dict] = []

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    for path in JSON_FILES:

        documents.extend(
            load_json_file(
                path
            )
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    for path in CSV_FILES:

        documents.extend(
            load_csv_file(
                path
            )
        )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    for path in PDF_FILES:

        documents.extend(
            load_pdf_file(
                path
            )
        )

    # ========================================================
    # DÉDUPLICATION
    # ========================================================

    unique_documents: list[dict] = []

    seen = set()

    for document in documents:

        # Déduplication basée principalement
        # sur le contenu complet.

        key = clean_text(
            document.get(
                "text",
                "",
            )
        ).casefold()

        if not key:

            continue

        if key in seen:

            continue

        seen.add(
            key
        )

        unique_documents.append(
            document
        )

    logger.info(
        "Corpus ESIC : %s documents uniques",
        len(unique_documents),
    )

    return unique_documents


# ============================================================
# ENCODAGE DES DOCUMENTS
# ============================================================

def encode_documents(
    model: SentenceTransformer,
    texts: list[str],
) -> np.ndarray:
    """
    Encode le corpus.

    Les versions récentes de
    sentence-transformers disposent
    de encode_document().

    On conserve encode() en fallback
    pour compatibilité.
    """

    if hasattr(
        model,
        "encode_document",
    ):

        embeddings = (
            model.encode_document(
                texts,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True,
            )
        )

    else:

        embeddings = (
            model.encode(
                texts,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True,
            )
        )

    return np.asarray(
        embeddings,
        dtype="float32",
    )


# ============================================================
# ENCODAGE DES QUESTIONS
# ============================================================

def encode_query(
    model: SentenceTransformer,
    question: str,
) -> np.ndarray:
    """
    Encode une question utilisateur.

    encode_query() est utilisé si disponible.
    """

    if hasattr(
        model,
        "encode_query",
    ):

        embedding = (
            model.encode_query(
                [question],
                convert_to_numpy=True,
            )
        )

    else:

        embedding = (
            model.encode(
                [question],
                convert_to_numpy=True,
            )
        )

    return np.asarray(
        embedding,
        dtype="float32",
    )


# ============================================================
# CONSTRUCTION DE L'INDEX FAISS
# ============================================================

def build_semantic_index() -> dict:
    """
    Reconstruit complètement l'index FAISS.
    """

    documents = (
        load_all_documents()
    )

    if not documents:

        raise RuntimeError(
            "Aucun document ESIC "
            "n'a été chargé."
        )

    # IMPORTANT :
    # Sentence-BERT encode search_text
    # et NON le gros contenu complet.

    texts = [

        document.get(
            "search_text",
            document.get(
                "text",
                "",
            ),
        )

        for document
        in documents
    ]

    model = (
        get_embedding_model()
    )

    embeddings = (
        encode_documents(
            model,
            texts,
        )
    )

    if (
        embeddings.ndim != 2
        or embeddings.shape[0] == 0
    ):

        raise RuntimeError(
            "Embeddings invalides."
        )

    # --------------------------------------------------------
    # Normalisation L2
    #
    # Avec IndexFlatIP :
    # produit scalaire sur vecteurs normalisés
    # = similarité cosinus.
    # --------------------------------------------------------

    faiss.normalize_L2(
        embeddings
    )

    dimension = int(
        embeddings.shape[1]
    )

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    # --------------------------------------------------------
    # Sauvegarde FAISS
    # --------------------------------------------------------

    faiss.write_index(
        index,
        str(INDEX_PATH),
    )

    # --------------------------------------------------------
    # Sauvegarde des documents
    # --------------------------------------------------------

    DOCUMENTS_PATH.write_text(

        json.dumps(
            documents,
            ensure_ascii=False,
            indent=2,
        ),

        encoding="utf-8",
    )

    # L'ancien index éventuellement
    # chargé en mémoire doit être invalidé.

    load_semantic_index.cache_clear()

    return {

        "documents":
            len(documents),

        "dimension":
            dimension,

        "index_path":
            str(
                INDEX_PATH
            ),

        "documents_path":
            str(
                DOCUMENTS_PATH
            ),
    }


# ============================================================
# CHARGEMENT DE L'INDEX
# ============================================================

@lru_cache(maxsize=1)
def load_semantic_index():
    """
    Charge FAISS et les métadonnées
    une seule fois.
    """

    if (
        not INDEX_PATH.exists()
        or not DOCUMENTS_PATH.exists()
    ):

        raise FileNotFoundError(
            "Index sémantique absent. "
            "Lancez : "
            "python scripts/"
            "build_semantic_index.py"
        )

    index = faiss.read_index(
        str(
            INDEX_PATH
        )
    )

    documents = json.loads(
        DOCUMENTS_PATH.read_text(
            encoding="utf-8"
        )
    )

    if (
        index.ntotal
        != len(documents)
    ):

        raise RuntimeError(
            "L'index FAISS et les "
            "métadonnées ne contiennent "
            "pas le même nombre "
            "de documents."
        )

    return (
        index,
        documents,
    )


# ============================================================
# RECHERCHE SÉMANTIQUE
# ============================================================

def semantic_search(
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """
    Recherche les documents ESIC
    sémantiquement les plus proches.
    """

    question = clean_text(
        question
    )

    if not question:

        return []

    index, documents = (
        load_semantic_index()
    )

    if index.ntotal == 0:

        return []

    model = (
        get_embedding_model()
    )

    query_embedding = (
        encode_query(
            model,
            question,
        )
    )

    # Même normalisation que le corpus.
    faiss.normalize_L2(
        query_embedding
    )

    k = min(
        max(
            1,
            int(top_k),
        ),
        index.ntotal,
    )

    scores, indices = (
        index.search(
            query_embedding,
            k,
        )
    )

    results: list[dict] = []

    for score, index_id in zip(
        scores[0],
        indices[0],
    ):

        if index_id < 0:

            continue

        document = documents[
            int(index_id)
        ]

        numeric_score = float(
            score
        )

        # ----------------------------------------------------
        # NIVEAU DE CONFIANCE
        # ----------------------------------------------------

        if (
            numeric_score
            >= ACCEPTED_THRESHOLD
        ):

            confidence = (
                "high"
            )

        elif (
            numeric_score
            >= LOW_THRESHOLD
        ):

            confidence = (
                "medium"
            )

        else:

            confidence = (
                "low"
            )

        result = {
            **document,

            "score":
                round(
                    numeric_score,
                    4,
                ),

            "confidence":
                confidence,

            "accepted": (
                numeric_score
                >= ACCEPTED_THRESHOLD
            ),
        }

        results.append(
            result
        )

    return results


# ============================================================
# MEILLEUR RÉSULTAT
# ============================================================

def best_semantic_match(
    question: str,
) -> dict | None:
    """
    Retourne le meilleur résultat,
    même s'il est sous le seuil de 0.70.

    Le code appelant peut ensuite utiliser
    result["accepted"] pour décider
    s'il est suffisamment fiable.
    """

    results = (
        semantic_search(
            question,
            top_k=1,
        )
    )

    if not results:

        return None

    return results[0]


# ============================================================
# MEILLEUR RÉSULTAT ACCEPTÉ
# ============================================================

def best_accepted_semantic_match(
    question: str,
) -> dict | None:
    """
    Retourne le meilleur résultat uniquement
    s'il atteint le seuil >= 0.70.
    """

    result = (
        best_semantic_match(
            question
        )
    )

    if not result:

        return None

    if not result.get(
        "accepted",
        False,
    ):

        return None

    return result


# ============================================================
# CONTEXTE POUR LE CHATBOT
# ============================================================

def get_semantic_context(
    question: str,
    limit: int = 3,
    minimum_score: float = LOW_THRESHOLD,
) -> list[dict]:
    """
    Fonction prévue pour l'intégration future
    dans response_service.py.

    Elle renvoie les meilleurs passages ayant
    au moins minimum_score.

    Pour le moment, elle peut être testée
    indépendamment du chatbot.
    """

    results = (
        semantic_search(
            question,
            top_k=max(
                limit,
                1,
            ),
        )
    )

    return [

        result

        for result
        in results

        if result.get(
            "score",
            0.0,
        )
        >= minimum_score

    ][:limit]


# ============================================================
# ÉTAT DE L'INDEX
# ============================================================

def get_semantic_index_status() -> dict:
    """
    Informations utiles pour les tests
    et le futur dashboard/admin.
    """

    exists = (
        INDEX_PATH.exists()
        and DOCUMENTS_PATH.exists()
    )

    result = {

        "ready":
            exists,

        "model":
            MODEL_NAME,

        "accepted_threshold":
            ACCEPTED_THRESHOLD,

        "low_threshold":
            LOW_THRESHOLD,

        "index_path":
            str(
                INDEX_PATH
            ),

        "documents_path":
            str(
                DOCUMENTS_PATH
            ),

        "documents":
            0,

        "dimension":
            None,
    }

    if not exists:

        return result

    try:

        index, documents = (
            load_semantic_index()
        )

        result[
            "documents"
        ] = len(
            documents
        )

        result[
            "dimension"
        ] = int(
            index.d
        )

    except Exception as exc:

        result[
            "ready"
        ] = False

        result[
            "error"
        ] = str(
            exc
        )

    return result