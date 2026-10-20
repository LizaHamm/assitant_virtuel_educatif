"""Service NLP de l'assistant virtuel éducatif ESIC.

Fonctionnalités :
- classification de la catégorie
- classification de l'intention
- extraction d'entités métier ESIC
- extraction de dates
- extraction de personnes et lieux avec spaCy
- détection des questions ambiguës
- détection des prédictions à faible confiance

Les modèles de classification sont chargés depuis :
    models/nlp/category_model.joblib
    models/nlp/intent_model.joblib
"""

from functools import lru_cache
from pathlib import Path
import re
import unicodedata
import threading

import joblib
import spacy


# ============================================================
# CHEMINS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[3]
MODEL_DIR = PROJECT_DIR / "models" / "nlp"


# ============================================================
# SEUILS DE CONFIANCE
# ============================================================

CATEGORY_LOW_CONFIDENCE = 0.45
INTENT_LOW_CONFIDENCE = 0.45


# ============================================================
# CHARGEMENT DES MODÈLES
# ============================================================

@lru_cache(maxsize=1)
def _load_models():
    category_path = MODEL_DIR / "category_model.joblib"
    intent_path = MODEL_DIR / "intent_model.joblib"

    missing = [
        str(path)
        for path in (category_path, intent_path)
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Modèles NLP manquants : "
            + ", ".join(missing)
            + ". Lancez backend/scripts/train_nlp_models.py "
              "depuis le projet."
        )

    category_model = joblib.load(category_path)
    intent_model = joblib.load(intent_path)

    return category_model, intent_model


@lru_cache(maxsize=1)
def _load_spacy():
    try:
        return spacy.load("fr_core_news_md")
    except OSError as exc:
        raise RuntimeError(
            "Le modèle spaCy fr_core_news_md n'est pas installé. "
            "Dans l'environnement virtuel du backend, exécutez : "
            "python -m spacy download fr_core_news_md"
        ) from exc


# ============================================================
# NORMALISATION
# ============================================================

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )


def unique(values):
    """Supprime les doublons tout en conservant l'ordre."""
    result = []
    seen = set()

    for value in values:
        key = normalize(str(value)).strip()

        if key and key not in seen:
            seen.add(key)
            result.append(value)

    return result


# ============================================================
# FORMATIONS
# ============================================================

FORMATION_ALIASES = {
    "Master IA": [
        "master ia",
        "master intelligence artificielle",
        "master en intelligence artificielle",
        "master d'intelligence artificielle",
        "m1 ia",
        "m2 ia",
        "ingenierie en intelligence artificielle",
        "ingénierie en intelligence artificielle",
    ],

    "CPDIA": [
        "cpdia",
    ],

    "Data Science": [
        "data science",
        "science des donnees",
        "science des données",
        "data scientist",
    ],

    "Bachelor": [
        "bachelor",
    ],

    "Cybersécurité": [
        "cybersecurite",
        "cybersécurité",
        "cyber securite",
        "cyber sécurité",
        "cybersecurity",
    ],

    "Développement": [
        "developpement",
        "développement",
        "developpement informatique",
        "développement informatique",
        "developpeur",
        "développeur",
    ],
}


# ============================================================
# SERVICES ESIC / CAMPUS
# ============================================================

SERVICE_ALIASES = {
    "Scolarité": [
        "scolarite",
        "scolarité",
        "service scolarite",
        "service scolarité",
        "secretariat pedagogique",
        "secrétariat pédagogique",
        "secretariat",
        "secrétariat",
    ],

    "Bibliothèque": [
        "bibliotheque",
        "bibliothèque",
        "mediatheque",
        "médiathèque",
    ],

    "Informatique": [
        "support informatique",
        "service informatique",
        "support technique",
        "service technique",
        "helpdesk",
    ],

    "Admissions": [
        "admission",
        "admissions",
        "service admission",
        "service admissions",
    ],

    "Restaurant universitaire": [
        "restaurant universitaire",
        "restaurant u",
        "resto u",
        "restaurant du campus",
    ],

    "Cafétéria": [
        "cafeteria",
        "cafétéria",
        "cafeteria du campus",
        "cafétéria du campus",
    ],

    "Santé": [
        "service de sante",
        "service de santé",
        "sante etudiante",
        "santé étudiante",
        "service medical",
        "service médical",
        "infirmerie",
        "infirmiere",
        "infirmière",
    ],

    "Soutien psychologique": [
        "soutien psychologique",
        "aide psychologique",
        "psychologue",
        "service psychologique",
    ],

    "Sports": [
        "service des sports",
        "service sport",
        "sport universitaire",
        "activites sportives",
        "activités sportives",
    ],

    "Associations étudiantes": [
        "association etudiante",
        "association étudiante",
        "associations etudiantes",
        "associations étudiantes",
        "vie associative",
        "bde",
        "bureau des etudiants",
        "bureau des étudiants",
    ],

    "Accueil": [
        "accueil",
        "accueil du campus",
        "accueil esic",
    ],

    "Ressources numériques": [
        "ressources numeriques",
        "ressources numériques",
        "plateforme numerique",
        "plateforme numérique",
        "espace numerique",
        "espace numérique",
    ],
}


# ============================================================
# LIEUX
# ============================================================

LOCATION_PATTERNS = [
    (
        "Salle",
        re.compile(
            r"\b(?:salle)\s+[A-Z]?\d{1,4}[A-Z]?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Amphithéâtre",
        re.compile(
            r"\b(?:amphi|amphitheatre|amphithéâtre)\s+"
            r"[A-Z]?\d{0,4}[A-Z]?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Bureau",
        re.compile(
            r"\b(?:bureau)\s+[A-Z]?\d{1,4}[A-Z]?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Bâtiment",
        re.compile(
            r"\b(?:batiment|bâtiment)\s+[A-Z0-9]+\b",
            re.IGNORECASE,
        ),
    ),
]


# ============================================================
# DATES
# ============================================================

MONTHS = (
    r"janvier|février|fevrier|mars|avril|mai|juin|juillet|"
    r"août|aout|septembre|octobre|novembre|décembre|decembre"
)

DATE_PATTERN = re.compile(
    rf"\b\d{{1,2}}[/-]\d{{1,2}}(?:[/-]\d{{2,4}})?\b"
    rf"|\b\d{{1,2}}\s+(?:{MONTHS})(?:\s+\d{{4}})?\b",
    re.IGNORECASE,
)

RELATIVE_DATE_PATTERNS = [
    r"\baujourd'hui\b",
    r"\baujourdhui\b",
    r"\bdemain\b",
    r"\bapres-demain\b",
    r"\baprès-demain\b",
    r"\bhier\b",
    r"\bce matin\b",
    r"\bcet apres-midi\b",
    r"\bcet après-midi\b",
    r"\bce soir\b",
    r"\bcette semaine\b",
    r"\bsemaine prochaine\b",
    r"\bla semaine prochaine\b",
    r"\bsemaine derniere\b",
    r"\bsemaine dernière\b",
    r"\blundi prochain\b",
    r"\bmardi prochain\b",
    r"\bmercredi prochain\b",
    r"\bjeudi prochain\b",
    r"\bvendredi prochain\b",
    r"\bsamedi prochain\b",
    r"\bdimanche prochain\b",
]


# ============================================================
# RECHERCHE D'ALIAS
# ============================================================

def find_aliases(
    text: str,
    aliases: dict[str, list[str]],
) -> list[str]:

    normalized = normalize(text)
    found = []

    for canonical, variants in aliases.items():
        for variant in variants:
            normalized_variant = normalize(variant)

            pattern = (
                r"(?<!\w)"
                + re.escape(normalized_variant)
                + r"(?!\w)"
            )

            if re.search(pattern, normalized):
                found.append(canonical)
                break

    return unique(found)


# ============================================================
# EXTRACTION DES DATES
# ============================================================

def extract_dates(text: str, doc) -> list[str]:
    dates = []

    # Dates numériques ou avec mois
    dates.extend(DATE_PATTERN.findall(text))

    # Dates relatives
    for pattern in RELATIVE_DATE_PATTERNS:
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            dates.append(match.group(0))

    # Dates détectées par spaCy
    for ent in doc.ents:
        if ent.label_ in {"DATE", "TIME"}:
            dates.append(ent.text)

    return unique(dates)


# ============================================================
# EXTRACTION DES LIEUX
# ============================================================

def extract_locations(text: str, doc) -> list[str]:
    locations = []

    # Règles spécifiques : salle, amphi, bureau, bâtiment
    for _, pattern in LOCATION_PATTERNS:
        for match in pattern.finditer(text):
            locations.append(match.group(0).strip())

    # Lieux génériques détectés par spaCy
    for ent in doc.ents:
        if ent.label_ in {"LOC", "GPE"}:
            value = ent.text.strip()

            # Éviter certaines erreurs fréquentes de spaCy
            normalized_value = normalize(value)

            false_locations = {
                "cpdia",
                "master ia",
                "data science",
                "bachelor",
                "aidez",
            }

            if normalized_value not in false_locations:
                locations.append(value)

    return unique(locations)


# ============================================================
# EXTRACTION DES PERSONNES
# ============================================================

def extract_people(doc) -> list[str]:
    people = []

    for ent in doc.ents:
        if ent.label_ in {"PER", "PERSON"}:
            people.append(ent.text.strip())

    return unique(people)


# ============================================================
# ENTITÉS NOMMÉES NETTOYÉES
# ============================================================

def clean_named_entities(
    doc,
    formations: list[str],
    services: list[str],
) -> list[dict]:

    named_entities = []

    known_business_terms = set()

    for canonical, variants in FORMATION_ALIASES.items():
        known_business_terms.add(normalize(canonical))

        for variant in variants:
            known_business_terms.add(normalize(variant))

    for canonical, variants in SERVICE_ALIASES.items():
        known_business_terms.add(normalize(canonical))

        for variant in variants:
            known_business_terms.add(normalize(variant))

    known_business_terms.update(
        {
            "aidez",
        }
    )

    for ent in doc.ents:
        value = ent.text.strip()
        normalized_value = normalize(value)

        # On évite d'afficher une formation ESIC comme faux LOC/MISC
        if normalized_value in known_business_terms:
            continue

        named_entities.append(
            {
                "text": value,
                "label": ent.label_,
            }
        )

    return named_entities


# ============================================================
# EXTRACTION GLOBALE DES ENTITÉS
# ============================================================

def extract_entities(text: str) -> dict:
    doc = _load_spacy()(text)

    formations = find_aliases(
        text,
        FORMATION_ALIASES,
    )

    services = find_aliases(
        text,
        SERVICE_ALIASES,
    )

    dates = extract_dates(
        text,
        doc,
    )

    locations = extract_locations(
        text,
        doc,
    )

    people = extract_people(doc)

    named_entities = clean_named_entities(
        doc,
        formations,
        services,
    )

    return {
        "formation": formations,
        "date": dates,
        "service": services,
        "personne": people,
        "lieu": locations,
        "named_entities": named_entities,
    }


# ============================================================
# PRÉDICTION CLASSIFICATION
# ============================================================

def predict(model, text: str) -> dict:
    probabilities = model.predict_proba([text])[0]
    classes = model.classes_

    best_index = probabilities.argmax()

    return {
        "label": str(classes[best_index]),
        "confidence": round(
            float(probabilities[best_index]),
            4,
        ),
        "probabilities": {
            str(label): round(float(probability), 4)
            for label, probability in zip(
                classes,
                probabilities,
            )
        },
    }


# ============================================================
# MESSAGES SOCIAUX
# ============================================================

SOCIAL_MESSAGES = {
    "bonjour",
    "bonsoir",
    "salut",
    "coucou",
    "hello",
    "hi",
    "hey",
    "merci",
    "merci beaucoup",
    "je te remercie",
    "thanks",
    "thank you",
    "au revoir",
    "bonne journee",
    "bonne soiree",
}


def is_social_message(text: str) -> bool:
    normalized = normalize(text).strip(
        " ?!.,;:"
    )

    return normalized in SOCIAL_MESSAGES


# ============================================================
# CLARIFICATION
# ============================================================

def detect_clarification(
    text: str,
    entities: dict,
    category: dict | None = None,
    intent: dict | None = None,
) -> dict:

    normalized = normalize(text).strip(
        " ?!.,;:"
    )

    # --------------------------------------------------------
    # Salutations / remerciements
    # --------------------------------------------------------

    if normalized in SOCIAL_MESSAGES:
        return {
            "required": False,
            "question": None,
            "reason": None,
        }

    # --------------------------------------------------------
    # Questions extrêmement vagues
    # --------------------------------------------------------

    vague_questions = {
        "c'est quand",
        "c est quand",
        "c'est ou",
        "c est ou",
        "et apres",
        "et après",
        "ou ca",
        "où ça",
        "quand",
        "ou",
        "où",
        "comment faire",
        "comment je fais",
        "je fais comment",
        "je dois faire quoi",
        "que faire",
        "et maintenant",
        "pour demain",
        "pour mon inscription",
        "pour mon dossier",
        "mon planning",
        "mon emploi du temps",
    }

    if normalized in {
        normalize(value)
        for value in vague_questions
    }:
        return {
            "required": True,
            "question": (
                "Pouvez-vous préciser votre demande ? "
                "Parlez-vous d'un cours, d'un examen, "
                "d'une formation, d'un service du campus "
                "ou d'une démarche administrative ?"
            ),
            "reason": "question_vague",
        }

    # --------------------------------------------------------
    # Planning trop vague
    # --------------------------------------------------------

    planning_terms = (
        "emploi du temps",
        "planning",
        "mes cours",
        "mon planning",
        "mon emploi du temps",
    )

    complaint_terms = (
        "faux",
        "incorrect",
        "incorrecte",
        "erreur",
        "probleme",
        "problème",
        "signaler",
        "reclamation",
        "réclamation",
        "contester",
    )

    mentions_planning = any(
        normalize(term) in normalized
        for term in planning_terms
    )

    is_complaint = any(
        normalize(term) in normalized
        for term in complaint_terms
    )

    if (
        mentions_planning
        and not entities.get("formation")
        and not is_complaint
    ):
        return {
            "required": True,
            "question": (
                "De quelle formation souhaitez-vous "
                "consulter l'emploi du temps ?"
            ),
            "reason": "formation_manquante",
        }

    # --------------------------------------------------------
    # Très faible confiance des DEUX modèles
    # --------------------------------------------------------

    if category and intent:
        category_confidence = category.get(
            "confidence",
            1.0,
        )

        intent_confidence = intent.get(
            "confidence",
            1.0,
        )

        if (
            category_confidence
            < CATEGORY_LOW_CONFIDENCE
            and intent_confidence
            < INTENT_LOW_CONFIDENCE
        ):
            return {
                "required": True,
                "question": (
                    "Je ne suis pas certain d'avoir bien "
                    "compris votre demande. Pouvez-vous "
                    "préciser le sujet et ce que vous "
                    "souhaitez obtenir ?"
                ),
                "reason": "faible_confiance",
            }

    return {
        "required": False,
        "question": None,
        "reason": None,
    }


# ============================================================
# ANALYSE NLP COMPLÈTE
# ============================================================

# Le pipeline spaCy + scikit est partagé par toutes les requêtes.
# Sous charge, exécuter le même pipeline 20 fois en parallèle sature inutilement
# le CPU. Le cache évite de recalculer les questions répétées et le verrou évite
# un "cache stampede" lors de requêtes simultanées identiques.
_ANALYZE_LOCK = threading.RLock()


@lru_cache(maxsize=2048)
def _analyze_question_cached(text: str) -> dict:
    category_model, intent_model = _load_models()

    category = predict(category_model, text)
    intent = predict(intent_model, text)
    entities = extract_entities(text)
    clarification = detect_clarification(
        text=text,
        entities=entities,
        category=category,
        intent=intent,
    )

    return {
        "category": category["label"],
        "category_confidence": category["confidence"],
        "category_probabilities": category["probabilities"],
        "category_low_confidence": category["confidence"] < CATEGORY_LOW_CONFIDENCE,
        "intent": intent["label"],
        "intent_confidence": intent["confidence"],
        "intent_probabilities": intent["probabilities"],
        "intent_low_confidence": intent["confidence"] < INTENT_LOW_CONFIDENCE,
        "entities": entities,
        "clarification": clarification,
    }


def analyze_question(text: str) -> dict:
    text = " ".join(str(text).strip().split())
    if not text:
        raise ValueError("La question ne peut pas être vide.")

    # Un seul calcul NLP CPU à la fois. Les questions répétées sont ensuite
    # servies directement depuis le cache.
    with _ANALYZE_LOCK:
        return _analyze_question_cached(text)
