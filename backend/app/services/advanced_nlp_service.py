"""NLP avancé ESIC.

Fonctionnalités :
- classification parmi 15 intentions sémantiques
- détection de sentiment
- score d'urgence
- recommandation d'escalade vers un humain
"""

from functools import lru_cache
from pathlib import Path
import re
import unicodedata

import joblib


PROJECT_DIR = (
    Path(__file__)
    .resolve()
    .parents[3]
)

MODEL_DIR = (
    PROJECT_DIR
    / "models"
    / "nlp"
)

SEMANTIC_MODEL_PATH = (
    MODEL_DIR
    / "semantic_intent_model.joblib"
)

SEMANTIC_LOW_CONFIDENCE = 0.45


# ============================================================
# NORMALISATION
# ============================================================

def normalize(text: str) -> str:

    text = unicodedata.normalize(
        "NFKD",
        str(text).casefold(),
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = re.sub(
        r"[^a-z0-9' -]+",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


# ============================================================
# MODÈLE 15 INTENTIONS
# ============================================================

@lru_cache(maxsize=1)
def _load_semantic_model():

    if not SEMANTIC_MODEL_PATH.exists():

        raise FileNotFoundError(
            "Modèle d'intention sémantique "
            "introuvable : "
            f"{SEMANTIC_MODEL_PATH}. "
            "Lancez : "
            "python scripts/"
            "train_semantic_intent.py"
        )

    return joblib.load(
        SEMANTIC_MODEL_PATH
    )


def predict_semantic_intent(
    text: str,
) -> dict:

    model = (
        _load_semantic_model()
    )

    probabilities = (
        model.predict_proba(
            [text]
        )[0]
    )

    classes = model.classes_

    best_index = int(
        probabilities.argmax()
    )

    confidence = float(
        probabilities[best_index]
    )

    return {

        "label":
            str(
                classes[best_index]
            ),

        "confidence":
            round(
                confidence,
                4,
            ),

        "low_confidence":
            confidence
            < SEMANTIC_LOW_CONFIDENCE,

        "probabilities": {
            str(label):
                round(
                    float(probability),
                    4,
                )

            for label, probability
            in zip(
                classes,
                probabilities,
            )
        },
    }


# ============================================================
# SENTIMENT / URGENCE
# ============================================================

FRUSTRATION_TERMS = (

    "inadmissible",
    "inacceptable",
    "scandaleux",
    "scandaleuse",
    "marre",

    "mecontent",
    "mecontente",

    "furieux",
    "furieuse",

    "enerve",
    "enervee",

    "frustre",
    "frustree",

    "aucune reponse",
    "toujours pas",
    "rien ne change",
    "pas normal",
    "honteux",

    "probleme non resolu",
    "dysfonctionnement",
)


URGENT_TERMS = (

    "urgent",
    "urgence",

    "immediatement",
    "au plus vite",
    "des maintenant",

    "avant aujourd'hui",
    "avant demain",

    "bloque",
    "bloquee",

    "impossible",

    "risque de perdre",

    "j'ai perdu",
    "jai perdu",

    "date limite",
    "dernier delai",

    "sans solution",
    "situation critique",
)


SATISFACTION_TERMS = (

    "merci",
    "parfait",
    "super",
    "excellent",

    "tres bien",

    "ça marche",
    "ca marche",

    "resolu",
    "resolue",

    "satisfait",
    "satisfaite",

    "merci beaucoup",

    "c'est clair",
    "c est clair",
)


NEGATION_SATISFACTION = (

    "pas satisfait",
    "pas satisfaite",

    "pas resolu",
    "pas resolue",

    "ne marche pas",
    "marche pas",

    "pas clair",
)


def _count_hits(
    normalized_text: str,
    terms: tuple[str, ...],
) -> int:

    return sum(
        1
        for term in terms
        if normalize(term)
        in normalized_text
    )


def detect_sentiment_urgency(
    text: str,
) -> dict:

    normalized = normalize(text)

    frustration_hits = (
        _count_hits(
            normalized,
            FRUSTRATION_TERMS,
        )
    )

    urgent_hits = (
        _count_hits(
            normalized,
            URGENT_TERMS,
        )
    )

    satisfaction_hits = (
        _count_hits(
            normalized,
            SATISFACTION_TERMS,
        )
    )

    negative_satisfaction_hits = (
        _count_hits(
            normalized,
            NEGATION_SATISFACTION,
        )
    )

    # "ça ne marche pas" ne doit
    # évidemment pas être considéré
    # comme de la satisfaction.
    if negative_satisfaction_hits:

        satisfaction_hits = 0

        frustration_hits += (
            negative_satisfaction_hits
        )

    urgency_score = 0.10

    if urgent_hits:

        urgency_score += min(
            0.70,
            0.40
            + 0.15
            * urgent_hits,
        )

    if frustration_hits:

        urgency_score += min(
            0.30,
            0.10
            * frustration_hits,
        )

    # Plusieurs points d'exclamation
    # constituent seulement un petit signal.
    if text.count("!") >= 2:

        urgency_score += 0.08

    urgency_score = round(
        min(
            1.0,
            urgency_score,
        ),
        2,
    )

    if (
        urgent_hits
        and urgency_score >= 0.55
    ):

        sentiment = "urgent"

    elif frustration_hits:

        sentiment = "frustration"

    elif satisfaction_hits:

        sentiment = "satisfaction"

    else:

        sentiment = "neutre"

    return {

        "sentiment":
            sentiment,

        "urgency_score":
            urgency_score,

        "human_escalation_recommended":
            urgency_score >= 0.70,

        "signals": {

            "frustration":
                frustration_hits,

            "urgent":
                urgent_hits,

            "satisfaction":
                satisfaction_hits,
        },
    }


# ============================================================
# ANALYSE AVANCÉE
# ============================================================

def analyze_advanced_nlp(
    text: str,
) -> dict:

    semantic = (
        predict_semantic_intent(
            text
        )
    )

    emotion = (
        detect_sentiment_urgency(
            text
        )
    )

    return {

        "semantic_intent":
            semantic["label"],

        "semantic_intent_confidence":
            semantic["confidence"],

        "semantic_intent_low_confidence":
            semantic["low_confidence"],

        "semantic_intent_probabilities":
            semantic["probabilities"],

        **emotion,
    }