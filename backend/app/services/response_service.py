
import csv
import re
import unicodedata
import threading
from pathlib import Path

from .knowledge_service import (
    get_service_hours,
    get_scolarite_contact,
    get_fraud_information,
    get_discipline_information,
    get_general_rules,
    get_rights_and_duties,
    get_security_rules,
    get_communication_rules,
    get_access_rules,
    get_campus_rules,
    format_calendar,
    get_formations,
    normalize_text,
    search_official_data,
)

# Recherche sémantique Sentence-BERT + FAISS.
# Le try/except permet au backend de rester utilisable même si l'index
# sémantique n'est pas encore construit sur une machine de développement.
try:
    from .semantic_search_service import (
        semantic_search,
        ACCEPTED_THRESHOLD as SEMANTIC_ACCEPTED_THRESHOLD,
        LOW_THRESHOLD as SEMANTIC_LOW_THRESHOLD,
    )
except Exception as exc:  # pragma: no cover - mode dégradé
    semantic_search = None
    SEMANTIC_ACCEPTED_THRESHOLD = 0.70
    SEMANTIC_LOW_THRESHOLD = 0.50
    print(f"[SEMANTIC SEARCH] Indisponible au chargement : {exc}")

# Modèle avancé : 15 intentions + sentiment/urgence.
# Il enrichit le reranking mais ne fabrique jamais de faits.
try:
    from .advanced_nlp_service import (
        analyze_advanced_nlp,
        detect_sentiment_urgency,
    )
except Exception as exc:  # pragma: no cover - mode dégradé
    analyze_advanced_nlp = None
    detect_sentiment_urgency = None
    print(f"[ADVANCED NLP] Indisponible au chargement : {exc}")


# ============================================================
# EMPLOI DU TEMPS — RECHERCHE DANS LE CSV
# ============================================================

DAYS_ORDER = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}


def is_timetable_question(question):
    q = normalize_text(question)

    keywords = [
        "emploi du temps",
        "planning",
        "planning des cours",
        "horaire des cours",
        "horaires des cours",
        "cours de cette semaine",
        "cours aujourd hui",
        "cours demain",
        "quand est mon cours",
        "quand sont mes cours",
    ]

    return any(keyword in q for keyword in keywords)


def load_timetable():
    """
    Charge le CSV de données situé dans backend/data.
    Ignore les deux lignes de métadonnées mal formées.
    """
    candidates = [
        Path(__file__).resolve().parents[2] / "data"
        / "emploi_du_temps_exclusive.csv",
        Path(__file__).resolve().parents[2] / "data"
        / "emploi_du_temps.csv",
    ]

    csv_path = next(
        (path for path in candidates if path.exists()),
        None,
    )

    if csv_path is None:
        return []

    # On repère l'en-tête dans les octets avant de décoder :
    # les métadonnées initiales du fichier ont un encodage différent.
    raw_lines = csv_path.read_bytes().splitlines()

    header_index = next(
        (
            i for i, line in enumerate(raw_lines)
            if line.lstrip().startswith(
                b"formation,groupe,semestre,jour,heure_debut"
            )
        ),
        None,
    )

    if header_index is None:
        return []

    csv_text = b"\n".join(raw_lines[header_index:])

    try:
        csv_text = csv_text.decode("utf-8-sig")
    except UnicodeDecodeError:
        csv_text = csv_text.decode("cp1252", errors="replace")

    rows = []

    reader = csv.DictReader(
        csv_text.splitlines(),
        delimiter=",",
    )

    for row in reader:
        cleaned = {}

        for key, value in row.items():
            if key is None:
                continue

            cleaned[key.strip()] = (
                value.strip().rstrip(";").strip()
                if value
                else ""
            )

        if cleaned.get("formation") and cleaned.get("groupe"):
            rows.append(cleaned)

    return rows


def detect_ia_level(question):
    q = normalize_text(question)

    if re.search(r"\bm2\b|master 2|master deux|deuxieme annee", q):
        return "M2"

    if re.search(r"\bm1\b|master 1|master un|premiere annee", q):
        return "M1"

    return None


def format_timetable(question):
    q = normalize_text(question)

    # Ne traiter ici que les questions de planning.
    if not is_timetable_question(q):
        return None

    level = detect_ia_level(q)
    mentions_ia = any(
        term in q
        for term in [
            "ia",
            "intelligence artificielle",
            "intelligence artificielle",
        ]
    )

    rows = load_timetable()

    if not rows:
        return (
            "Je ne peux pas afficher l'emploi du temps : "
            "le fichier de planning est introuvable ou illisible."
        )

    # Reconnaissance de la formation demandée.
    if mentions_ia:
        if level is None:
            return (
                "Tu recherches l'emploi du temps de quel niveau "
                "en Intelligence Artificielle : Master 1 (M1-IA) "
                "ou Master 2 (M2-IA) ?"
            )

        formation_code = f"{level}-IA"

    else:
        # Recherche d'un code de formation explicite.
        formation_code = None

        for row in rows:
            code = row.get("formation", "").strip().upper()

            if code and normalize_text(code) in q:
                formation_code = code
                break

        if formation_code is None:
            return (
                "Pour retrouver le bon emploi du temps, indique "
                "ta formation (par exemple M1-IA ou M2-IA)."
            )

    matching_rows = [
        row for row in rows
        if row.get("formation", "").strip().upper()
        == formation_code
    ]

    if not matching_rows:
        return (
            f"Je n'ai pas trouvé d'emploi du temps pour "
            f"{formation_code} dans les données disponibles. "
            "Je préfère te le signaler plutôt que d'inventer "
            "des cours."
        )

    # Filtrer le semestre uniquement si l'utilisateur le demande.
    semester_match = re.search(r"\bs([12])\b", q)

    if semester_match:
        semester = f"S{semester_match.group(1)}"
        matching_rows = [
            row for row in matching_rows
            if row.get("semestre", "").strip().upper() == semester
        ]

        if not matching_rows:
            return (
                f"Aucun cours du semestre {semester} n'a été trouvé "
                f"pour {formation_code}."
            )

    group_codes = sorted({
        row.get("groupe", "").strip()
        for row in matching_rows
        if row.get("groupe")
    })

    # Si plusieurs groupes existent, ne pas choisir arbitrairement.
    requested_group = next(
        (
            group for group in group_codes
            if normalize_text(group) in q
        ),
        None,
    )

    if len(group_codes) > 1 and requested_group is None:
        return (
            f"J'ai trouvé plusieurs groupes pour {formation_code} : "
            f"{', '.join(group_codes)}. "
            "Indique ton groupe pour obtenir le planning exact."
        )

    if requested_group:
        matching_rows = [
            row for row in matching_rows
            if row.get("groupe", "").strip() == requested_group
        ]

    matching_rows.sort(
        key=lambda row: (
            DAYS_ORDER.get(
                normalize_text(row.get("jour", "")), 99
            ),
            row.get("heure_debut", ""),
        )
    )

    semester = matching_rows[0].get("semestre", "non précisé")
    group = matching_rows[0].get("groupe", "non précisé")

    response = (
        f"Voici l'emploi du temps disponible pour "
        f"{formation_code}, groupe {group}, semestre {semester}.\n\n"
    )

    current_day = None

    for row in matching_rows:
        day = row.get("jour", "Jour non précisé")

        if day != current_day:
            response += f"\n{day}\n"
            current_day = day

        start = row.get("heure_debut", "?")
        end = row.get("heure_fin", "?")
        subject = row.get("matiere_nom", "Matière non précisée")
        course_type = row.get("type_cours", "")
        room = row.get("salle_nom", "")
        teacher = row.get("enseignant_nom", "")

        response += f"- {start}–{end} : {subject}"

        if course_type:
            response += f" ({course_type})"

        if room:
            response += f" — Salle : {room}"

        if teacher:
            response += f" — Enseignant : {teacher}"

        response += "\n"

    response += (
        "\nAttention : ces données proviennent du fichier de planning "
        "du projet. Vérifie auprès de la scolarité qu'elles correspondent "
        "à l'année universitaire actuelle."
    )

    return response.strip()


# ============================================================
# US-006 — HORAIRES DES SERVICES
# ============================================================

def is_hours_question(question):
    question = normalize_text(question)

    keywords = [
        "horaire", "horaires", "heure", "heures",
        "ouvre", "ouvert", "ouverture", "ferme", "fermeture",
        "quand est ouvert", "quand ouvre", "quand ferme",
    ]

    return any(keyword in question for keyword in keywords)


# ============================================================
# US-007 — CONTACT SCOLARITÉ
# ============================================================

def is_scolarite_contact_question(question):
    question = normalize_text(question)

    contact_keywords = [
        "contact", "contacter", "joindre", "email", "mail",
        "telephone", "tel", "numero", "coordonnees", "adresse",
    ]

    scolarite_keywords = ["scolarite", "scolaire"]

    return (
        any(k in question for k in contact_keywords)
        and any(k in question for k in scolarite_keywords)
    )


# ============================================================
# US-008 — RÈGLES DU CAMPUS
# ============================================================

def is_campus_rules_question(question):
    question = normalize_text(question)

    keywords = [
        "regles du campus", "reglement interieur", "reglement",
        "regles de vie", "vie du campus", "regles generales",
        "regles esic", "regles de l esic", "droits et devoirs",
        "discipline", "sanctions", "securite",
        "securite du campus", "acces aux locaux",
    ]

    return any(k in question for k in keywords)


def is_fraud_question(question):
    question = normalize_text(question)

    return any(k in question for k in [
        "fraude", "frauder", "plagiat", "plagier", "triche",
        "tricher", "triche examen", "fraude examen", "sanction fraude",
    ])


def is_discipline_question(question):
    question = normalize_text(question)

    return any(k in question for k in [
        "discipline", "sanction", "sanctions", "conseil de discipline",
        "exclusion", "exclu", "avertissement", "blame",
    ])


def is_rights_duties_question(question):
    question = normalize_text(question)

    return any(k in question for k in [
        "droits et devoirs", "droits des etudiants",
        "devoirs des etudiants", "obligations des etudiants",
        "obligations etudiants",
    ])


def is_security_question(question):
    question = normalize_text(question)

    return any(k in question for k in [
        "securite", "securite du campus", "regles de securite",
        "incendie", "evacuation", "issue de secours",
        "issues de secours", "urgence", "accident",
    ])


def is_access_question(question):
    question = normalize_text(question)

    return any(k in question for k in [
        "acces aux locaux", "acces au campus", "acceder au campus",
        "horaires du campus", "fermeture du campus",
        "ouverture du campus",
    ])


# ============================================================
# US-009 — CALENDRIER
# ============================================================

def is_calendar_question(question):
    """Réserve format_calendar() aux demandes réellement globales.

    Une question précise comme « Quand ont lieu les rattrapages ? » doit
    passer par la FAQ/FAISS afin d'obtenir uniquement le passage pertinent.
    """
    question = normalize_text(question)

    keywords = [
        "calendrier universitaire",
        "calendrier academique",
        "calendrier scolaire",
        "dates importantes",
        "date importante",
        "toutes les dates",
        "calendrier de l annee",
        "calendrier de l annee universitaire",
    ]

    return any(k in question for k in keywords)


# ============================================================
# DÉTECTION DU SERVICE
# ============================================================

def detect_service(question):
    question = normalize_text(question)

    services = {
        "bibliotheque": ["bibliotheque", "mediatheque"],
        "restaurant": ["restaurant", "restaurant universitaire", "restaurant u"],
        "cafeteria": ["cafeteria"],
        "infirmerie": ["infirmerie", "infirmiere", "sante"],
        "helpdesk": ["helpdesk", "informatique", "service informatique", "support informatique"],
        "scolarite": ["scolarite"],
        "accueil": ["accueil"],
        "musculation": ["musculation", "salle de musculation", "salle musculation"],
    }

    for service, keywords in services.items():
        if any(keyword in question for keyword in keywords):
            return service

    return None


# ============================================================
# FORMATAGE DES HORAIRES
# ============================================================

def format_hours(service_name, result):
    if not result:
        return None

    horaires = result.get("horaires", {})

    labels = {
        "lundi_vendredi": "Lundi à vendredi",
        "samedi": "Samedi",
        "dimanche": "Dimanche",
        "periode_examens": "Période d'examens",
        "chat_en_ligne": "Chat en ligne",
        "lundi": "Lundi",
        "mardi": "Mardi",
        "mercredi": "Mercredi",
        "jeudi": "Jeudi",
        "vendredi": "Vendredi",
    }

    service_labels = {
        "bibliotheque": "la bibliothèque",
        "restaurant_universitaire": "le restaurant universitaire",
        "cafeteria": "la cafétéria",
        "infirmerie": "l'infirmerie",
        "helpdesk_informatique": "le helpdesk informatique",
        "scolarite": "la scolarité",
        "accueil_general": "l'accueil",
        "salle_musculation": "la salle de musculation",
    }

    display_name = service_labels.get(result.get("service"), service_name)
    response = f"Les horaires de {display_name} sont :\n"

    for key, value in horaires.items():
        label = labels.get(key, key.replace("_", " ").capitalize())
        response += f"- {label} : {value}\n"

    return response.strip()


# ============================================================
# FORMATAGE CONTACT SCOLARITÉ
# ============================================================

def format_scolarite_contact(contact):
    if not contact:
        return None

    responsable = contact.get("responsable", {})
    equipe = contact.get("equipe", [])

    response = (
        "Voici les coordonnées du service Scolarité :\n\n"
        f"- Responsable : {responsable.get('prenom', '')} "
        f"{responsable.get('nom', '')}\n"
        f"- Email : {responsable.get('email', 'Non renseigné')}\n"
        f"- Téléphone : {responsable.get('telephone', 'Non renseigné')}\n"
        f"- Bureau : {contact.get('bureau', 'Non renseigné')}\n"
        f"- Bâtiment : {contact.get('batiment', 'Non renseigné')}\n"
        f"- Horaires : {contact.get('horaires', 'Non renseignés')}"
    )

    if equipe:
        response += "\n\nÉquipe de la scolarité :"

        for personne in equipe:
            response += (
                f"\n- {personne.get('prenom', '')} "
                f"{personne.get('nom', '')}"
                f" — {personne.get('poste', '')}"
                f" — {personne.get('email', '')}"
                f" — {personne.get('telephone', '')}"
            )

    return response


# ============================================================
# US-010 — FORMATIONS PROPOSÉES AUX VISITEURS
# ============================================================

def is_formations_question(question):
    question = normalize_text(question)

    formation_keywords = [
        "formation", "formations", "programme", "programmes",
        "filiere", "filieres", "cursus", "etudes", "etudier",
        "parcours", "diplome", "diplomes",
    ]

    visitor_keywords = [
        "visiteur", "visiteurs", "visite", "visiter", "prospect",
        "prospects", "futur etudiant", "future etudiante",
        "lyceen", "lyceenne", "candidat", "candidats",
        "quelles formations", "quels programmes", "quels cursus",
    ]

    return (
        any(k in question for k in formation_keywords)
        and any(k in question for k in visitor_keywords)
    )


def format_formations(formations):
    if not formations:
        return None

    response = "Voici les formations proposées par l'ESIC :\n\n"

    for formation in formations:
        code = formation.get("code", "")
        nom = formation.get("nom", "")
        niveau = formation.get("niveau", "")
        groupes = formation.get("groupes", [])

        response += f"- {nom or code}"

        if code:
            response += f" ({code})"

        if niveau:
            response += f" — {niveau}"

        if groupes:
            response += f" — Groupes : {', '.join(groupes)}"

        response += "\n"

    return response.strip()


# ============================================================
# RÉPONSE PRINCIPALE + RECHERCHE NLP / BASE DE CONNAISSANCES
# ============================================================

# Le NLP ne fabrique pas la réponse : il sert à ROUTER la recherche.
# La réponse factuelle vient ensuite de la base de connaissances ESIC.
CATEGORY_SOURCE_PRIORITY = {
    "Emplois du temps et planning": ("timetable", "faq", "procedures", "contacts"),
    "Procédures administratives": ("procedures", "faq", "contacts", "timetable"),
    "Services campus": ("faq", "contacts", "procedures", "timetable"),
    "Règlement et vie étudiante": ("faq", "procedures", "contacts", "timetable"),
    "Orientation et formation": ("faq", "procedures", "contacts", "timetable"),
    "Contacts et information générale": ("contacts", "faq", "procedures", "timetable"),
}

STOPWORDS = {
    "a", "ai", "au", "aux", "avec", "ce", "ces", "cette", "comment",
    "dans", "de", "des", "du", "elle", "en", "est", "et", "etre", "faire",
    "il", "je", "la", "le", "les", "ma", "mes", "mon", "ne", "nous", "on",
    "ou", "par", "pas", "peut", "pour", "pourquoi", "qu", "que", "quel",
    "quelle", "quelles", "quels", "qui", "sa", "se", "ses", "son", "sont",
    "sur", "tu", "un", "une", "vos", "votre", "vous", "y",
}

QUESTION_KEYS = ("question", "demande", "intitule", "intitulé")
ANSWER_KEYS = ("reponse", "réponse", "answer", "solution")
TITLE_KEYS = ("titre", "title", "nom", "name", "service", "formation")
USEFUL_KEYS = {
    "question", "demande", "intitule", "intitulé",
    "reponse", "réponse", "answer", "solution",
    "titre", "title", "nom", "name", "description", "contenu", "content",
    "procedure", "procédure", "etapes", "étapes", "prerequis", "prérequis",
    "documents_necessaires", "documents nécessaires", "documents_requis",
    "email", "mail", "telephone", "téléphone", "adresse", "bureau", "batiment",
    "bâtiment", "horaires", "date", "periode", "période", "duree_estimee",
    "durée_estimee", "categorie", "catégorie", "formation", "service",
    "responsable", "equipe", "équipe", "poste", "public_concerne",
}


def _normalize_search_text(value) -> str:
    text = unicodedata.normalize("NFKD", str(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _normalized_key(value) -> str:
    return _normalize_search_text(value).replace(" ", "_")


def _tokens(value) -> set[str]:
    return {
        token
        for token in _normalize_search_text(value).split()
        if len(token) >= 2 and token not in STOPWORDS
    }


def _value_for_keys(record: dict, keys) -> object | None:
    if not isinstance(record, dict):
        return None

    normalized = {_normalized_key(key): key for key in record.keys()}
    for wanted in keys:
        actual = normalized.get(_normalized_key(wanted))
        if actual is not None:
            value = record.get(actual)
            if value not in (None, "", [], {}):
                return value
    return None


def _record_has_any_key(record: dict, keys) -> bool:
    if not isinstance(record, dict):
        return False
    present = {_normalized_key(key) for key in record.keys()}
    return any(_normalized_key(key) in present for key in keys)


def _is_atomic_knowledge_record(record: dict) -> bool:
    """Détermine si un dict correspond à UNE connaissance exploitable.

    On évite volontairement de considérer le document FAQ complet comme une
    réponse. Une entrée Q/R, une procédure, un contact ou une ligne de planning
    peut en revanche devenir un candidat de recherche.
    """
    if not isinstance(record, dict) or not record:
        return False

    has_question = _record_has_any_key(record, QUESTION_KEYS)
    has_answer = _record_has_any_key(record, ANSWER_KEYS)
    if has_question and has_answer:
        return True

    keys = {_normalized_key(key) for key in record.keys()}

    # Procédure individuelle.
    if ("titre" in keys or "nom" in keys) and (
        "etapes" in keys
        or "prerequis" in keys
        or "documents_necessaires" in keys
        or "documents_requis" in keys
    ):
        return True

    # Contact/service individuel.
    if (
        ("email" in keys or "telephone" in keys or "bureau" in keys)
        and ("nom" in keys or "service" in keys or "responsable" in keys or "poste" in keys)
    ):
        return True

    # Ligne d'emploi du temps.
    if "formation" in keys and "jour" in keys and (
        "heure_debut" in keys or "horaire" in keys
    ):
        return True

    return False


def _iter_atomic_records(value, depth: int = 0):
    """Aplatit un gros JSON et renvoie les petites unités pertinentes.

    C'est la correction essentielle du bug qui affichait les 150 FAQ : le
    document racine est traversé, mais il n'est jamais envoyé tel quel au chat.
    """
    if depth > 12:
        return

    if isinstance(value, dict):
        if _is_atomic_knowledge_record(value):
            yield value

        # Même lorsqu'une procédure est déjà une connaissance atomique, elle
        # peut contenir des FAQ internes plus précises : on les indexe aussi.
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from _iter_atomic_records(child, depth + 1)

    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                yield from _iter_atomic_records(child, depth + 1)


def _record_to_text(record) -> str:
    """Convertit UNE entrée de connaissance en texte court et indexable."""
    if isinstance(record, str):
        return record.strip()

    if isinstance(record, list):
        parts = [_record_to_text(value) for value in record]
        return "\n".join(part for part in parts if part)

    if not isinstance(record, dict):
        return str(record).strip()

    lines = []
    for key, value in record.items():
        if value in (None, "", [], {}):
            continue

        normalized_key = _normalized_key(key)
        if normalized_key not in {_normalized_key(k) for k in USEFUL_KEYS}:
            continue

        if isinstance(value, dict):
            value = _record_to_text(value)
        elif isinstance(value, list):
            formatted = []
            for item in value:
                if isinstance(item, dict):
                    item_text = _record_to_text(item)
                else:
                    item_text = str(item).strip()
                if item_text:
                    formatted.append(item_text)
            value = " ; ".join(formatted)

        value = str(value).strip()
        if value:
            lines.append(f"{str(key).replace('_', ' ').capitalize()} : {value}")

    return "\n".join(lines).strip()


def _nlp_entities(nlp_result: dict | None) -> list[str]:
    if not nlp_result:
        return []

    entities = nlp_result.get("entities") or {}
    values = []
    for key in ("formation", "service", "date", "lieu", "personne"):
        for value in entities.get(key, []) or []:
            if isinstance(value, str) and value.strip():
                values.append(value.strip())
    return list(dict.fromkeys(values))


def _source_priority(nlp_result: dict | None) -> tuple[str, ...]:
    if not nlp_result:
        return ("faq", "procedures", "contacts", "timetable")

    category = nlp_result.get("category")
    confidence = float(nlp_result.get("category_confidence") or 0.0)

    # Si le classifieur hésite beaucoup, on ne ferme aucune porte.
    if confidence < 0.30:
        return ("faq", "procedures", "contacts", "timetable")

    return CATEGORY_SOURCE_PRIORITY.get(
        category,
        ("faq", "procedures", "contacts", "timetable"),
    )


def _score_candidate(
    question: str,
    record: dict,
    source: str,
    source_rank: int,
    base_score: float,
    nlp_result: dict | None,
) -> float:
    question_tokens = _tokens(question)
    record_text = _record_to_text(record)
    record_tokens = _tokens(record_text)

    if not question_tokens or not record_tokens:
        return 0.0

    overlap = len(question_tokens & record_tokens) / len(question_tokens)

    record_question = _value_for_keys(record, QUESTION_KEYS)
    if record_question:
        q_tokens = _tokens(record_question)
        question_overlap = (
            len(question_tokens & q_tokens) / len(question_tokens)
            if q_tokens else 0.0
        )
    else:
        question_overlap = 0.0

    title = _value_for_keys(record, TITLE_KEYS)
    if title:
        title_tokens = _tokens(title)
        title_overlap = (
            len(question_tokens & title_tokens) / len(question_tokens)
            if title_tokens else 0.0
        )
    else:
        title_overlap = 0.0

    # Le score fourni par knowledge_service reste un petit signal seulement :
    # un gros document racine peut avoir un score élevé sans être la bonne réponse.
    try:
        raw_base = max(float(base_score), 0.0)
    except (TypeError, ValueError):
        raw_base = 0.0
    base_component = raw_base / (raw_base + 5.0) if raw_base else 0.0

    entity_boost = 0.0
    normalized_record = _normalize_search_text(record_text)
    entities = _nlp_entities(nlp_result)
    entity_matches = 0
    for entity in entities:
        normalized_entity = _normalize_search_text(entity)
        if normalized_entity and normalized_entity in normalized_record:
            entity_matches += 1
            entity_boost += 0.10

    # Une entité explicite (ex. Master IA) est un filtre très important : une
    # procédure générique contenant le mot "prérequis" ne doit pas battre une
    # fiche qui parle réellement du Master IA.
    entity_penalty = -0.25 if entities and entity_matches == 0 else 0.0

    record_keys = {_normalized_key(key) for key in record.keys()}
    normalized_question = _normalize_search_text(question)
    field_boost = 0.0

    if any(term in normalized_question for term in (
        "piece", "pieces", "document", "documents", "fournir", "justificatif", "justificatifs"
    )) and ("documents_necessaires" in record_keys or "documents_requis" in record_keys):
        field_boost += 0.25

    if any(term in normalized_question for term in (
        "prerequis", "condition admission", "conditions admission", "admissible"
    )) and "prerequis" in record_keys:
        field_boost += 0.20

    if any(term in normalized_question for term in (
        "contact", "contacter", "joindre", "email", "mail", "telephone", "numero"
    )) and ("email" in record_keys or "telephone" in record_keys or "responsable" in record_keys):
        field_boost += 0.15

    # Le routage NLP donne un léger avantage aux sources prioritaires sans
    # empêcher une autre source de gagner si son contenu correspond mieux.
    source_boost = max(0.0, 0.08 - (source_rank * 0.02))

    return (
        0.45 * overlap
        + 0.25 * question_overlap
        + 0.20 * title_overlap
        + 0.10 * base_component
        + min(entity_boost, 0.20)
        + field_boost
        + entity_penalty
        + source_boost
    )


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


_ADVANCED_NLP_LOCK = threading.RLock()
_ADVANCED_NLP_CACHE: dict[str, dict] = {}


def _get_advanced_nlp(question: str) -> dict:
    """Exécute les 15 intentions + sentiment/urgence sans contention CPU.

    Le résultat est mémorisé par question et un seul thread calcule une nouvelle
    question à la fois. Cela évite que plusieurs requêtes simultanées lancent
    les mêmes modèles en concurrence.
    """
    key = _normalize_search_text(question)
    with _ADVANCED_NLP_LOCK:
        cached = _ADVANCED_NLP_CACHE.get(key)
        if cached is not None:
            return dict(cached)

        result: dict = {}

        if analyze_advanced_nlp is not None:
            try:
                advanced = analyze_advanced_nlp(question)
                if isinstance(advanced, dict):
                    result.update(advanced)
            except Exception as exc:
                print(f"[ADVANCED NLP] Erreur classification : {exc}")

        # analyze_advanced_nlp renvoie déjà sentiment/urgence dans la version
        # actuelle. On n'appelle le détecteur séparé que si une valeur manque.
        needs_emotion = not result.get("sentiment") or not (
            result.get("urgency") or result.get("urgence")
        )
        if needs_emotion and detect_sentiment_urgency is not None:
            try:
                emotion = detect_sentiment_urgency(question)
                if isinstance(emotion, dict):
                    for name, value in emotion.items():
                        result.setdefault(name, value)
                elif isinstance(emotion, (tuple, list)) and len(emotion) >= 2:
                    result.setdefault("sentiment", emotion[0])
                    result.setdefault("urgency", emotion[1])
            except Exception as exc:
                print(f"[ADVANCED NLP] Erreur sentiment/urgence : {exc}")

        if len(_ADVANCED_NLP_CACHE) >= 2048:
            _ADVANCED_NLP_CACHE.clear()
        _ADVANCED_NLP_CACHE[key] = dict(result)
        return dict(result)

def _advanced_intent(advanced_result: dict | None) -> str:
    if not advanced_result:
        return ""

    # Compatibilité avec plusieurs noms de clés possibles du service avancé.
    for key in (
        "semantic_intent",
        "intent",
        "predicted_intent",
        "intention",
    ):
        value = advanced_result.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_search_text(value).replace(" ", "_")

    semantic = advanced_result.get("semantic")
    if isinstance(semantic, dict):
        for key in ("intent", "label", "semantic_intent"):
            value = semantic.get(key)
            if isinstance(value, str) and value.strip():
                return _normalize_search_text(value).replace(" ", "_")

    return ""


def _advanced_confidence(advanced_result: dict | None) -> float:
    if not advanced_result:
        return 0.0

    for key in (
        "semantic_intent_confidence",
        "intent_confidence",
        "confidence",
        "score",
    ):
        if key in advanced_result:
            return _safe_float(advanced_result.get(key), 0.0)

    semantic = advanced_result.get("semantic")
    if isinstance(semantic, dict):
        for key in ("confidence", "score"):
            if key in semantic:
                return _safe_float(semantic.get(key), 0.0)

    return 0.0


def _advanced_sentiment_urgency(advanced_result: dict | None) -> tuple[str, str]:
    """Récupère sentiment/urgence si le service avancé les renvoie."""
    if not advanced_result:
        return "", ""

    sentiment = advanced_result.get("sentiment")
    urgency = advanced_result.get("urgency") or advanced_result.get("urgence")

    if isinstance(sentiment, dict):
        sentiment = sentiment.get("label") or sentiment.get("sentiment")
    if isinstance(urgency, dict):
        urgency = urgency.get("label") or urgency.get("urgency") or urgency.get("urgence")

    return (
        _normalize_search_text(sentiment or "").replace(" ", "_"),
        _normalize_search_text(urgency or "").replace(" ", "_"),
    )


def _source_kind_from_filename(source: str) -> str:
    normalized = _normalize_search_text(source)
    if "emploi" in normalized or "timetable" in normalized or "planning" in normalized:
        return "timetable"
    if "contact" in normalized or "annuaire" in normalized:
        return "contacts"
    if "procedure" in normalized:
        return "procedures"
    if "reglement" in normalized:
        return "reglement"
    if "guide" in normalized:
        return "guide"
    if "faq" in normalized:
        return "faq"
    return "knowledge"


def _semantic_record(result: dict) -> dict:
    """Convertit un résultat FAISS dans le format utilisé par le moteur lexical."""
    data = result.get("data")
    document_type = result.get("type")

    # JSON atomique : on conserve la structure pour pouvoir extraire reponse,
    # prerequis, documents_necessaires, email, etc.
    if isinstance(data, dict) and document_type != "pdf":
        record = dict(data)
        if record:
            return record

    # PDF : data contient surtout page/chunk ; le fait utile est dans text.
    record = {
        "titre": result.get("label") or result.get("source") or "Document ESIC",
        "contenu": result.get("text") or "",
    }

    if isinstance(data, dict):
        if data.get("page") is not None:
            record["page"] = data.get("page")
        if data.get("chunk") is not None:
            record["chunk"] = data.get("chunk")

    return record


def _question_requirements(question: str) -> set[str]:
    q = _normalize_search_text(question)
    requirements = set()

    if any(term in q for term in (
        "prerequis", "condition admission", "conditions admission",
        "integrer", "admission", "admis", "admissible",
    )):
        requirements.add("prerequisites")

    if any(term in q for term in (
        "document", "documents", "piece", "pieces", "justificatif",
        "justificatifs", "fournir",
    )):
        requirements.add("documents")

    if any(term in q for term in (
        "contact", "contacter", "joindre", "email", "mail",
        "telephone", "numero", "coordonnees",
    )):
        requirements.add("contact")

    if any(term in q for term in (
        "metier", "metiers", "debouche", "debouches", "carriere",
        "carriere", "travailler apres", "emploi apres",
    )):
        requirements.add("careers")

    if any(term in q for term in (
        "rattrapage", "rattrapages", "examen", "examens",
    )):
        requirements.add("exams")

    return requirements


def _evidence_adjustment(question: str, record: dict) -> float:
    """Récompense les passages qui contiennent réellement le type de fait demandé."""
    requirements = _question_requirements(question)
    if not requirements:
        return 0.0

    text = _normalize_search_text(_record_to_text(record))
    keys = {_normalized_key(key) for key in record.keys()} if isinstance(record, dict) else set()
    adjustment = 0.0

    if "prerequisites" in requirements:
        has_evidence = (
            "prerequis" in keys
            or "prerequis" in text
            or "conditions d admission" in text
            or "condition d admission" in text
            or "admission" in text
        )
        adjustment += 0.14 if has_evidence else -0.22

    if "documents" in requirements:
        has_evidence = (
            "documents_necessaires" in keys
            or "documents_requis" in keys
            or "documents necessaires" in text
            or "pieces a fournir" in text
            or "justificatifs" in text
        )
        adjustment += 0.12 if has_evidence else -0.10

    if "contact" in requirements:
        has_evidence = (
            "email" in keys
            or "telephone" in keys
            or "responsable" in keys
            or "@" in _record_to_text(record)
        )
        adjustment += 0.12 if has_evidence else -0.12

    if "careers" in requirements:
        career_markers = (
            "data engineer", "data analyst", "data scientist", "ai engineer",
            "ai researcher", "ingenieur", "consultant", "chef de projet",
            "debouches", "metiers", "carriere",
        )
        has_evidence = any(marker in text for marker in career_markers)
        adjustment += 0.18 if has_evidence else -0.12

    if "exams" in requirements:
        has_evidence = any(term in text for term in (
            "rattrapage", "rattrapages", "examen", "examens",
        ))
        adjustment += 0.10 if has_evidence else -0.08

    return adjustment


def _advanced_routing_boost(
    record: dict,
    source: str,
    advanced_result: dict | None,
) -> float:
    """Petit bonus de reranking issu du classifieur des 15 intentions."""
    intent = _advanced_intent(advanced_result)
    if not intent:
        return 0.0

    confidence = _advanced_confidence(advanced_result)
    # Même avec une faible confiance, le signal reste petit et ne peut pas
    # écraser le contenu documentaire.
    weight = 0.06 if confidence < 0.45 else 0.10

    source_kind = _source_kind_from_filename(source)
    text = _normalize_search_text(_record_to_text(record))

    expected = {
        "emploi_du_temps": {"timetable", "faq"},
        "procedure_admin": {"procedures", "faq", "contacts"},
        "service_campus": {"faq", "contacts", "guide"},
        "reglement": {"reglement", "faq", "procedures"},
        "formation": {"guide", "faq", "procedures"},
        "contact": {"contacts", "faq", "procedures"},
        "aide_technique": {"faq", "contacts"},
        "reclamation": {"procedures", "contacts", "faq"},
        "information_generale": {"faq", "guide"},
        "examen": {"faq", "reglement", "timetable"},
        "vie_etudiante": {"faq", "guide", "contacts"},
    }

    boost = weight if source_kind in expected.get(intent, set()) else 0.0

    # Quelques intentions peuvent aussi être reconnues directement dans le texte.
    if intent == "formation" and any(term in text for term in (
        "formation", "master", "bachelor", "data science", "intelligence artificielle"
    )):
        boost += 0.04
    elif intent == "contact" and ("@" in _record_to_text(record) or "telephone" in text):
        boost += 0.04
    elif intent == "reglement" and any(term in text for term in (
        "reglement", "sanction", "fraude", "discipline"
    )):
        boost += 0.04

    return min(boost, 0.14)


def _candidate_signature(record: dict) -> str:
    return _normalize_search_text(_record_to_text(record))


def _lexical_candidates(
    question: str,
    nlp_result: dict | None,
    advanced_result: dict | None,
    limit: int,
) -> list[dict]:
    sources = _source_priority(nlp_result)
    candidates = []

    for source_rank, source in enumerate(sources):
        try:
            found = search_official_data(
                source,
                question,
                limit=max(12, limit * 5),
            )
        except Exception as exc:
            print(f"[ESIC SEARCH] Erreur pour {source}: {exc}")
            continue

        for item in found or []:
            if not isinstance(item, dict):
                continue

            root_record = item.get("record", {})
            base_score = item.get("score", 0.0)
            atomic_records = list(_iter_atomic_records(root_record))

            if not atomic_records and _is_atomic_knowledge_record(root_record):
                atomic_records = [root_record]

            for record in atomic_records:
                lexical_score = _score_candidate(
                    question=question,
                    record=record,
                    source=source,
                    source_rank=source_rank,
                    base_score=base_score,
                    nlp_result=nlp_result,
                )

                lexical_score += _evidence_adjustment(question, record)
                lexical_score += _advanced_routing_boost(
                    record, source, advanced_result
                )

                if lexical_score >= 0.20:
                    candidates.append({
                        "source": source,
                        "score": round(lexical_score, 4),
                        "hybrid_score": round(lexical_score, 4),
                        "lexical_score": round(lexical_score, 4),
                        "semantic_score": None,
                        "record": record,
                        "retrieval": "lexical",
                    })

    return candidates


_SEMANTIC_LOCK = threading.RLock()
_SEMANTIC_CACHE: dict[tuple[str, int], list[dict]] = {}


def _semantic_search_cached(question: str, top_k: int) -> list[dict]:
    """Sentence-BERT/FAISS partagé, sérialisé et mis en cache.

    PyTorch/SentenceTransformer peut devenir extrêmement lent si plusieurs
    threads CPU appellent encode() simultanément. Un seul encodage est donc
    exécuté à la fois ; les questions répétées sont servies depuis le cache.
    """
    if semantic_search is None:
        return []

    key = (_normalize_search_text(question), int(top_k))
    with _SEMANTIC_LOCK:
        cached = _SEMANTIC_CACHE.get(key)
        if cached is not None:
            return [dict(item) for item in cached]

        found = semantic_search(question, top_k=top_k) or []
        clean = [dict(item) for item in found if isinstance(item, dict)]
        if len(_SEMANTIC_CACHE) >= 2048:
            _SEMANTIC_CACHE.clear()
        _SEMANTIC_CACHE[key] = clean
        return [dict(item) for item in clean]


def _semantic_candidates(
    question: str,
    nlp_result: dict | None,
    advanced_result: dict | None,
    limit: int,
) -> list[dict]:
    if semantic_search is None:
        return []

    try:
        found = _semantic_search_cached(
            question,
            top_k=max(10, limit * 4),
        )
    except Exception as exc:
        # Index absent/corrompu : le moteur lexical continue de fonctionner.
        print(f"[SEMANTIC SEARCH] Erreur : {exc}")
        return []

    candidates = []
    priority = _source_priority(nlp_result)

    for item in found or []:
        if not isinstance(item, dict):
            continue

        semantic_score = _safe_float(item.get("score"), 0.0)
        record = _semantic_record(item)
        source = str(item.get("source") or "semantic")
        source_kind = _source_kind_from_filename(source)

        try:
            source_rank = priority.index(source_kind)
        except ValueError:
            source_rank = len(priority)

        lexical_signal = _score_candidate(
            question=question,
            record=record,
            source=source_kind,
            source_rank=source_rank,
            base_score=0.0,
            nlp_result=nlp_result,
        )

        # Le score lexical peut dépasser 1 avec les bonus de champs :
        # on le borne uniquement pour la fusion avec le cosinus.
        lexical_component = min(max(lexical_signal, 0.0), 1.0)

        hybrid_score = (
            0.62 * semantic_score
            + 0.38 * lexical_component
            + _evidence_adjustment(question, record)
            + _advanced_routing_boost(record, source, advanced_result)
        )

        # Une FAQ dont la question est presque identique mérite un petit bonus.
        record_question = _value_for_keys(record, QUESTION_KEYS)
        if record_question:
            q_tokens = _tokens(question)
            faq_tokens = _tokens(record_question)
            if q_tokens and faq_tokens:
                overlap = len(q_tokens & faq_tokens) / len(q_tokens)
                if overlap >= 0.75:
                    hybrid_score += 0.10

        candidates.append({
            "source": source,
            "score": round(hybrid_score, 4),
            "hybrid_score": round(hybrid_score, 4),
            "lexical_score": round(lexical_signal, 4),
            "semantic_score": round(semantic_score, 4),
            "semantic_confidence": item.get("confidence"),
            "semantic_accepted": bool(item.get("accepted")),
            "record": record,
            "retrieval": "semantic",
            "document_type": item.get("type"),
            "label": item.get("label"),
        })

    return candidates


def _merge_candidates(candidates: list[dict], limit: int) -> list[dict]:
    """Fusionne les doublons lexical/FAISS et conserve le meilleur score."""
    merged: dict[str, dict] = {}

    for item in candidates:
        record = item.get("record") or {}
        signature = _candidate_signature(record)
        if not signature:
            continue

        current = merged.get(signature)
        if current is None:
            merged[signature] = dict(item)
            continue

        # Si le même passage est retrouvé par les deux moteurs, c'est un signal
        # de confiance supplémentaire.
        current_methods = set(str(current.get("retrieval", "")).split("+"))
        new_methods = set(str(item.get("retrieval", "")).split("+"))
        methods = {method for method in current_methods | new_methods if method}

        if item.get("hybrid_score", 0.0) > current.get("hybrid_score", 0.0):
            best = dict(item)
            other = current
        else:
            best = dict(current)
            other = item

        semantic_values = [
            value for value in (best.get("semantic_score"), other.get("semantic_score"))
            if value is not None
        ]
        lexical_values = [
            value for value in (best.get("lexical_score"), other.get("lexical_score"))
            if value is not None
        ]

        if semantic_values:
            best["semantic_score"] = max(semantic_values)
        if lexical_values:
            best["lexical_score"] = max(lexical_values)

        # Accord des deux moteurs : petit bonus, jamais suffisant à lui seul.
        agreement_bonus = 0.06 if {"semantic", "lexical"}.issubset(methods) else 0.0
        best["hybrid_score"] = round(
            max(
                _safe_float(best.get("hybrid_score")),
                _safe_float(other.get("hybrid_score")),
            ) + agreement_bonus,
            4,
        )
        best["score"] = best["hybrid_score"]
        best["retrieval"] = "+".join(sorted(methods))
        merged[signature] = best

    ordered = sorted(
        merged.values(),
        key=lambda item: item.get("hybrid_score", item.get("score", 0.0)),
        reverse=True,
    )

    return ordered[:limit]


_KNOWLEDGE_SEARCH_LOCK = threading.RLock()
_KNOWLEDGE_SEARCH_CACHE: dict[tuple, list[dict]] = {}


def _nlp_cache_signature(nlp_result: dict | None) -> tuple:
    if not isinstance(nlp_result, dict):
        return ()
    entities = nlp_result.get("entities") or {}
    formations = tuple(str(v) for v in (entities.get("formation") or []))
    services = tuple(str(v) for v in (entities.get("service") or []))
    return (
        str(nlp_result.get("category") or ""),
        str(nlp_result.get("intent") or ""),
        formations,
        services,
    )


def search_esic_knowledge(
    question: str,
    nlp_result: dict | None = None,
    limit: int = 3,
) -> list:
    """Recherche hybride optimisée pour la concurrence.

    1. recherche lexicale très rapide ;
    2. si le résultat lexical est déjà fort, retour immédiat ;
    3. sinon seulement : modèle 15 intentions + Sentence-BERT/FAISS ;
    4. cache + single-flight pour éviter 20 calculs identiques en parallèle.
    """
    normalized = _normalize_search_text(question)
    cache_key = (normalized, _nlp_cache_signature(nlp_result), int(limit))

    with _KNOWLEDGE_SEARCH_LOCK:
        cached = _KNOWLEDGE_SEARCH_CACHE.get(cache_key)
        if cached is not None:
            return [dict(item) for item in cached]

        # FAST PATH : pas de modèle lourd tant que la recherche lexicale suffit.
        lexical_fast = _lexical_candidates(
            question,
            nlp_result=nlp_result,
            advanced_result=None,
            limit=max(limit, 3),
        )
        lexical_fast = _merge_candidates(lexical_fast, limit=limit)

        if lexical_fast:
            best = lexical_fast[0]
            lexical_score = _safe_float(best.get("lexical_score"), 0.0)
            evidence = _evidence_adjustment(question, best.get("record") or {})
            if lexical_score >= 0.58 and evidence >= -0.05:
                result = lexical_fast[:limit]
                if len(_KNOWLEDGE_SEARCH_CACHE) >= 2048:
                    _KNOWLEDGE_SEARCH_CACHE.clear()
                _KNOWLEDGE_SEARCH_CACHE[cache_key] = result
                return [dict(item) for item in result]

        # SLOW PATH : seulement quand le lexical n'est pas assez certain.
        advanced_result = _get_advanced_nlp(question)
        lexical = _lexical_candidates(
            question,
            nlp_result=nlp_result,
            advanced_result=advanced_result,
            limit=max(limit, 3),
        )
        semantic = _semantic_candidates(
            question,
            nlp_result=nlp_result,
            advanced_result=advanced_result,
            limit=max(limit, 3),
        )
        result = _merge_candidates(lexical + semantic, limit=limit)

        if len(_KNOWLEDGE_SEARCH_CACHE) >= 2048:
            _KNOWLEDGE_SEARCH_CACHE.clear()
        _KNOWLEDGE_SEARCH_CACHE[cache_key] = result
        return [dict(item) for item in result]

def _candidate_is_reliable(result: dict, question: str) -> bool:
    """Décide si un passage est assez solide pour être montré à l'utilisateur."""
    if not result:
        return False

    hybrid = _safe_float(result.get("hybrid_score", result.get("score")), 0.0)
    semantic = result.get("semantic_score")
    semantic_value = _safe_float(semantic, 0.0) if semantic is not None else None
    lexical = _safe_float(result.get("lexical_score"), 0.0)

    # Sentence-BERT >= 0.70 : seuil explicite du cahier des charges.
    if semantic_value is not None and semantic_value >= SEMANTIC_ACCEPTED_THRESHOLD:
        return True

    # Zone moyenne 0.50-0.70 : on exige l'accord du reranking hybride.
    if (
        semantic_value is not None
        and semantic_value >= SEMANTIC_LOW_THRESHOLD
        and hybrid >= 0.56
    ):
        # Pour les demandes factuelles ciblées, le passage doit réellement
        # contenir le type d'information demandé.
        if _evidence_adjustment(question, result.get("record") or {}) < -0.05:
            return False
        return True

    # Recherche lexicale seule : on accepte seulement un candidat fort.
    if semantic_value is None and lexical >= 0.48 and hybrid >= 0.48:
        if _evidence_adjustment(question, result.get("record") or {}) < -0.05:
            return False
        return True

    return False

def _format_scalar_or_list(value) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                text = _record_to_text(item)
            else:
                text = str(item).strip()
            if text:
                parts.append(text)
        return "\n".join(f"- {part}" for part in parts)
    if isinstance(value, dict):
        return _record_to_text(value)
    return str(value).strip()


def format_best_knowledge_answer(result: dict, question: str | None = None) -> str | None:
    """Transforme le meilleur candidat en réponse utilisateur, jamais en dump JSON."""
    if not result:
        return None

    record = result.get("record") or {}
    if not isinstance(record, dict):
        text = str(record).strip()
        return text[:2500] if text else None

    # Cas idéal : FAQ question/réponse. On renvoie la réponse, pas toute la FAQ.
    answer = _value_for_keys(record, ANSWER_KEYS)
    if answer:
        answer_text = _format_scalar_or_list(answer).strip()
        return answer_text[:3000] if answer_text else None

    # Procédure : titre + éléments réellement utiles seulement.
    title = _value_for_keys(record, TITLE_KEYS)
    description = _value_for_keys(record, ("description", "contenu", "content"))
    prereqs = _value_for_keys(record, ("prerequis", "prérequis"))
    documents = _value_for_keys(
        record,
        ("documents_necessaires", "documents nécessaires", "documents_requis"),
    )
    steps = _value_for_keys(record, ("etapes", "étapes", "procedure", "procédure"))

    # Si la question vise un champ précis, ne pas noyer l'utilisateur dans
    # toute la procédure.
    normalized_question = _normalize_search_text(question or "")
    if documents and any(term in normalized_question for term in (
        "piece", "pieces", "document", "documents", "fournir", "justificatif", "justificatifs"
    )):
        heading = f"{title}\n\n" if title else ""
        return (heading + "Documents nécessaires :\n" + _format_scalar_or_list(documents))[:3000]

    if prereqs and any(term in normalized_question for term in (
        "prerequis", "condition admission", "conditions admission", "admissible"
    )):
        heading = f"{title}\n\n" if title else ""
        return (heading + "Prérequis :\n" + _format_scalar_or_list(prereqs))[:3000]

    sections = []
    if title:
        sections.append(str(title).strip())
    if description:
        sections.append(str(description).strip())
    if prereqs:
        formatted = _format_scalar_or_list(prereqs)
        if formatted:
            sections.append("Prérequis :\n" + formatted)
    if documents:
        formatted = _format_scalar_or_list(documents)
        if formatted:
            sections.append("Documents nécessaires :\n" + formatted)
    if steps:
        formatted = _format_scalar_or_list(steps)
        if formatted:
            sections.append("Étapes :\n" + formatted)

    if sections:
        return "\n\n".join(sections)[:3500]

    # Contact ou autre petite fiche : seulement les champs utiles déjà filtrés.
    content = _record_to_text(record)
    return content[:2500] if content else None


def format_esic_knowledge(results: list) -> str:
    """Contexte compact pour debug/RAG, sans exposer un document complet."""
    sections = []
    for item in results:
        answer = format_best_knowledge_answer(item)
        if answer:
            sections.append(
                f"[Source ESIC : {item.get('source', 'inconnue')} | "
                f"score={item.get('score', 0):.2f}]\n{answer}"
            )
    return "\n\n".join(sections)


def get_esic_context(question: str, nlp_result: dict | None = None) -> str:
    """Retourne au maximum 3 extraits pertinents pour un futur moteur RAG/LLM."""
    return format_esic_knowledge(
        search_esic_knowledge(question, nlp_result=nlp_result, limit=3)
    )


def generate_response(question: str, nlp_result: dict | None = None):
    """Génère une réponse ESIC en combinant règles, NLP et base de connaissances.

    Ordre :
    1. règles déterministes pour les données structurées sûres ;
    2. NLP pour router la recherche documentaire ;
    3. récupération du meilleur passage de la base ESIC ;
    4. réponse prudente si aucune connaissance suffisamment pertinente n'existe.
    """
    question = " ".join(str(question).strip().split())
    question_normalized = normalize_text(question)

    # Salutations avant toute recherche documentaire.
    if question_normalized in {
        "bonjour", "bonsoir", "salut", "coucou", "hello", "hi", "hey",
    }:
        return (
            "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. "
            "Comment puis-je vous aider aujourd'hui ?"
        )

    if (
        question_normalized == "merci"
        or question_normalized.startswith("merci ")
        or question_normalized in {"thanks", "thank you", "je te remercie"}
    ):
        return "Avec plaisir ! N'hésitez pas si vous avez d'autres questions."

    if question_normalized in {
        "au revoir", "a bientot", "bonne journee", "bonne soiree",
    }:
        return "Au revoir ! Bonne journée et à bientôt."

    # 1) Données structurées / règles existantes.
    timetable_response = format_timetable(question_normalized)
    if timetable_response is not None:
        return timetable_response

    if is_scolarite_contact_question(question_normalized):
        response = format_scolarite_contact(get_scolarite_contact())
        if response:
            return response

    if is_fraud_question(question_normalized):
        fraud = get_fraud_information()
        if fraud:
            return (
                "Voici les informations du règlement intérieur concernant "
                "la fraude et le plagiat :\n\n" + fraud
            )

    if is_discipline_question(question_normalized):
        discipline = get_discipline_information()
        if discipline:
            return (
                "Voici les informations du règlement intérieur concernant "
                "la discipline et les sanctions :\n\n" + discipline
            )

    if is_rights_duties_question(question_normalized):
        information = get_rights_and_duties()
        if information:
            return (
                "Voici les droits et devoirs des étudiants selon le règlement "
                "intérieur :\n\n" + information
            )

    if is_security_question(question_normalized):
        information = get_security_rules()
        if information:
            return (
                "Voici les règles de sécurité et de santé du règlement "
                "intérieur :\n\n" + information
            )

    if is_access_question(question_normalized):
        information = get_access_rules()
        if information:
            return "Voici les règles concernant l'accès aux locaux :\n\n" + information

    if is_campus_rules_question(question_normalized):
        information = get_campus_rules()
        if information:
            return (
                "Voici les principales règles du campus selon le règlement "
                "intérieur de l'ESIC :\n\n" + information
            )

    if is_hours_question(question_normalized):
        service = detect_service(question_normalized)
        if service:
            response = format_hours(service, get_service_hours(service))
            if response:
                return response

        # Une question vague sur "les horaires" peut demander tous les services.
        all_hours = get_service_hours()
        if all_hours:
            labels = {
                "accueil_general": "Accueil",
                "scolarite": "Scolarité",
                "bibliotheque": "Bibliothèque",
                "restaurant_universitaire": "Restaurant universitaire",
                "cafeteria": "Cafétéria",
                "salle_musculation": "Salle de musculation",
                "infirmerie": "Infirmerie",
                "helpdesk_informatique": "Helpdesk informatique",
            }
            lines = ["Voici les principaux horaires des services du campus :"]
            for key, horaires in all_hours.items():
                lines.append(f"\n{labels.get(key, key.replace('_', ' ').capitalize())} :")
                for jour, valeur in horaires.items():
                    lines.append(
                        f"- {jour.replace('_', ' ').capitalize()} : {valeur}"
                    )
            return "\n".join(lines).strip()

    # Cette règle ne répond qu'à "quelles formations proposez-vous ?".
    # Les prérequis/débouchés/modules d'une formation passent par la base FAQ.
    if is_formations_question(question_normalized):
        response = format_formations(get_formations())
        if response:
            return response

    if is_calendar_question(question_normalized):
        calendar = format_calendar()
        if calendar:
            return calendar

    # 2) Recherche hybride : NLP + modèle 15 intentions + lexical + SBERT/FAISS.
    results = search_esic_knowledge(
        question,
        nlp_result=nlp_result,
        limit=5,
    )

    if results:
        best = results[0]
        if _candidate_is_reliable(best, question):
            answer = format_best_knowledge_answer(best, question=question)
            if answer:
                return answer

    # 3) Pas de réponse fiable : ne rien inventer.
    # On utilise sentiment/urgence uniquement pour adapter le fallback, jamais
    # pour créer une information absente de la base.
    advanced_result = _get_advanced_nlp(question)
    _, urgency = _advanced_sentiment_urgency(advanced_result)

    if urgency in {"high", "haute", "urgent", "urgente", "critique", "elevee", "eleve"}:
        return (
            "Je n'ai pas trouvé de réponse suffisamment précise dans la base de "
            "connaissances ESIC pour cette demande urgente. Contacte rapidement "
            "le service concerné ou la scolarité afin d'obtenir une confirmation."
        )

    return (
        "Je n'ai pas trouvé de réponse suffisamment précise dans la base de "
        "connaissances ESIC. Peux-tu préciser ta demande ?"
    )
