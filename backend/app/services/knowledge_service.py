import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader


# ============================================================
# CHEMINS DU PROJET
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

CONTACTS_FILE = DATA_DIR / "annuaire_contacts.json"
CALENDAR_FILE = DATA_DIR / "emploi_du_temps.json"


# ============================================================
# NORMALISATION
# ============================================================

def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower().strip()

    text = unicodedata.normalize("NFD", text)

    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    return " ".join(text.split())


# ============================================================
# CHARGEMENT JSON
# ============================================================

def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    except FileNotFoundError:
        print(f"[ERREUR] Fichier introuvable : {file_path}")
        return {}

    except json.JSONDecodeError as error:
        print(
            f"[ERREUR] JSON invalide dans {file_path} : {error}"
        )
        return {}


# ============================================================
# ANNUAIRE / US-006 / US-007
# ============================================================

def load_knowledge():
    return load_json(CONTACTS_FILE)


def get_service_hours(service_name=None):
    data = load_knowledge()

    horaires = data.get("horaires_services", {})

    if not service_name:
        return horaires

    service_name = normalize_text(service_name)

    aliases = {
        "accueil": "accueil_general",
        "accueil general": "accueil_general",

        "scolarite": "scolarite",

        "bibliotheque": "bibliotheque",
        "mediatheque": "bibliotheque",

        "restaurant": "restaurant_universitaire",
        "restaurant u": "restaurant_universitaire",
        "restaurant universitaire": "restaurant_universitaire",

        "cafeteria": "cafeteria",

        "infirmerie": "infirmerie",
        "infirmiere": "infirmerie",

        "helpdesk": "helpdesk_informatique",
        "informatique": "helpdesk_informatique",
        "helpdesk informatique": "helpdesk_informatique",
        "service informatique": "helpdesk_informatique",
        "support informatique": "helpdesk_informatique",

        "salle de musculation": "salle_musculation",
        "salle musculation": "salle_musculation",
        "musculation": "salle_musculation",
    }

    key = aliases.get(service_name)

    if key and key in horaires:
        return {
            "service": key,
            "horaires": horaires[key],
        }

    return None


def get_scolarite_contact():
    data = load_knowledge()

    services = data.get(
        "services_administratifs",
        []
    )

    for service in services:

        service_name = normalize_text(
            service.get("service", "")
        )

        if service_name == "scolarite":
            return service

    return None


# ============================================================
# RÈGLEMENT INTÉRIEUR / US-008
# ============================================================

def find_reglement_pdf():
    if not DATA_DIR.exists():
        return None

    pdf_files = list(DATA_DIR.glob("*.pdf"))

    # Priorité au fichier contenant "reglement interieur"
    for file in pdf_files:

        normalized_name = normalize_text(file.name)

        if "reglement interieur" in normalized_name:
            return file

    # Fallback sur n'importe quel PDF contenant "reglement"
    for file in pdf_files:

        normalized_name = normalize_text(file.name)

        if "reglement" in normalized_name:
            return file

    return None


REGLEMENT_FILE = find_reglement_pdf()


@lru_cache(maxsize=1)
def load_reglement_text():
    if REGLEMENT_FILE is None:

        print(
            "[ERREUR] Aucun règlement intérieur PDF trouvé."
        )

        return ""

    try:

        reader = PdfReader(str(REGLEMENT_FILE))

        pages = []

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                pages.append(page_text)

        return "\n".join(pages)

    except Exception as error:

        print(
            f"[ERREUR] Lecture du règlement : {error}"
        )

        return ""


# ============================================================
# EXTRACTION D'UNE SECTION DU PDF
# ============================================================

def extract_section_from_pdf(
    section_title,
    next_section_title=None
):
    """
    Extrait une section du règlement intérieur.

    Le PDF contient notamment une table des matières.
    On cherche donc toutes les occurrences du titre et
    on utilise la dernière occurrence, correspondant
    normalement au contenu réel de la section.

    La normalisation des espaces permet également de gérer
    les retours à la ligne introduits par l'extraction PDF.
    """

    text = load_reglement_text()

    if not text:
        return None

    normalized_text = normalize_text(text)
    normalized_title = normalize_text(section_title)

    if not normalized_title:
        return None

    # Chercher toutes les occurrences du titre.
    positions = [
        match.start()
        for match in re.finditer(
            re.escape(normalized_title),
            normalized_text
        )
    ]

    if not positions:
        return None

    # Dernière occurrence = contenu réel plutôt que sommaire.
    start = positions[-1]

    if next_section_title:

        normalized_next = normalize_text(
            next_section_title
        )

        next_positions = [
            match.start()
            for match in re.finditer(
                re.escape(normalized_next),
                normalized_text
            )
            if match.start() > start
        ]

        if next_positions:
            end = next_positions[0]
        else:
            end = len(normalized_text)

    else:
        end = len(normalized_text)

    section = normalized_text[start:end].strip()

    return section


# ============================================================
# NETTOYAGE DES SECTIONS DU PDF
# ============================================================

def clean_pdf_section(section):
    if not section:
        return None

    lines = []

    for line in section.splitlines():

        line = line.strip()

        if not line:
            continue

        # Retirer les lignes de pointillés de sommaire.
        if "...." in line:
            continue

        # Retirer les lignes composées uniquement d'un numéro.
        if re.fullmatch(r"\d+", line):
            continue

        lines.append(line)

    if not lines:
        return None

    return "\n".join(lines).strip()


# ============================================================
# FRAUDE / PLAGIAT
# ============================================================

def get_fraud_information():

    section = extract_section_from_pdf(
        "5.3 Fraude et plagiat",
        "5.4 Résultats et délibérations",
    )

    return clean_pdf_section(section)


# ============================================================
# DISCIPLINE ET SANCTIONS
# ============================================================

def get_discipline_information():

    section = extract_section_from_pdf(
        "10. DISCIPLINE ET SANCTIONS",
        "11. RÉCLAMATIONS ET RECOURS",
    )

    return clean_pdf_section(section)


# ============================================================
# RÈGLES GÉNÉRALES DU CAMPUS
# ============================================================

def get_general_rules():

    section = extract_section_from_pdf(
        "1. PRÉAMBULE ET DISPOSITIONS GÉNÉRALES",
        "2. ADMISSION ET INSCRIPTION",
    )

    return clean_pdf_section(section)


# ============================================================
# DROITS ET DEVOIRS
# ============================================================

def get_rights_and_duties():

    section = extract_section_from_pdf(
        "8. DROITS ET DEVOIRS DES ÉTUDIANTS",
        "9. VIE ÉTUDIANTE ET ASSOCIATIONS",
    )

    return clean_pdf_section(section)


# ============================================================
# SÉCURITÉ ET SANTÉ
# ============================================================

def get_security_rules():

    section = extract_section_from_pdf(
        "12.2 SÉCURITÉ ET SANTÉ",
        "12.3 COMMUNICATION ET AFFICHAGE",
    )

    return clean_pdf_section(section)


# ============================================================
# COMMUNICATION ET AFFICHAGE
# ============================================================

def get_communication_rules():

    section = extract_section_from_pdf(
        "12.3 COMMUNICATION ET AFFICHAGE",
        "12.4 ACCÈS AUX LOCAUX",
    )

    return clean_pdf_section(section)


# ============================================================
# ACCÈS AUX LOCAUX
# ============================================================

def get_access_rules():

    section = extract_section_from_pdf(
        "12.4 ACCÈS AUX LOCAUX",
        "12.5 ENVIRONNEMENT ET DÉVELOPPEMENT DURABLE",
    )

    return clean_pdf_section(section)


# ============================================================
# RÈGLES DU CAMPUS
# ============================================================

def get_campus_rules():

    sections = []

    general_rules = get_general_rules()

    if general_rules:
        sections.append(
            "1. PRÉAMBULE ET DISPOSITIONS GÉNÉRALES\n"
            + general_rules
        )

    rights_duties = get_rights_and_duties()

    if rights_duties:
        sections.append(
            "8. DROITS ET DEVOIRS DES ÉTUDIANTS\n"
            + rights_duties
        )

    discipline = get_discipline_information()

    if discipline:
        sections.append(
            "10. DISCIPLINE ET SANCTIONS\n"
            + discipline
        )

    security = get_security_rules()

    if security:
        sections.append(
            "12.2 SÉCURITÉ ET SANTÉ\n"
            + security
        )

    communication = get_communication_rules()

    if communication:
        sections.append(
            "12.3 COMMUNICATION ET AFFICHAGE\n"
            + communication
        )

    access = get_access_rules()

    if access:
        sections.append(
            "12.4 ACCÈS AUX LOCAUX\n"
            + access
        )

    if not sections:
        return None

    return "\n\n".join(sections)


# ============================================================
# RECHERCHE PAR MOTS-CLÉS
# ============================================================

def find_lines_containing_keywords(
    text,
    keywords
):
    if not text:
        return []

    normalized_keywords = [
        normalize_text(keyword)
        for keyword in keywords
    ]

    results = []

    for line in text.splitlines():

        clean_line = line.strip()

        if not clean_line:
            continue

        normalized_line = normalize_text(
            clean_line
        )

        if any(
            keyword in normalized_line
            for keyword in normalized_keywords
        ):
            results.append(clean_line)

    return results


# ============================================================
# CALENDRIER / US-009
# ============================================================

def load_calendar():
    return load_json(CALENDAR_FILE)


def get_calendar_metadata():

    data = load_calendar()

    return data.get(
        "metadata",
        {}
    )

def get_formations():
    data = load_calendar()
    formations = data.get("formations", [])

    if not formations:
        return None

    return formations

def get_semesters():

    data = load_calendar()

    return data.get(
        "metadata",
        {}
    ).get(
        "semestres",
        []
    )


def get_important_dates():

    data = load_calendar()

    important_dates = []

    metadata = data.get(
        "metadata",
        {}
    )

    semesters = metadata.get(
        "semestres",
        []
    )

    for semester in semesters:

        semester_name = semester.get(
            "semestre",
            ""
        )

        if semester.get("debut"):

            important_dates.append({
                "type": "Début du semestre",
                "semestre": semester_name,
                "date": semester["debut"],
            })

        if semester.get("fin"):

            important_dates.append({
                "type": "Fin du semestre",
                "semestre": semester_name,
                "date": semester["fin"],
            })

        vacances = semester.get(
            "vacances",
            []
        )

        for vacation in vacances:

            important_dates.append({
                "type": f"Vacances — {vacation.get('nom', '')}",
                "semestre": semester_name,
                "debut": vacation.get("debut"),
                "fin": vacation.get("fin"),
            })

        examens = semester.get(
            "examens"
        )

        if examens:

            important_dates.append({
                "type": "Examens",
                "semestre": semester_name,
                "debut": examens.get("debut"),
                "fin": examens.get("fin"),
            })

        stages = semester.get(
            "stages"
        )

        if stages:

            important_dates.append({
                "type": "Stages",
                "semestre": semester_name,
                "debut": stages.get("debut"),
                "fin": stages.get("fin"),
            })

    return important_dates


def format_calendar():

    dates = get_important_dates()

    if not dates:
        return None

    response = (
        "Voici les principales dates du calendrier :\n\n"
    )

    for item in dates:

        item_type = item.get(
            "type",
            "Date"
        )

        semester = item.get(
            "semestre",
            ""
        )

        if item.get("date"):

            response += f"- {item_type}"

            if semester:
                response += f" ({semester})"

            response += (
                f" : {item['date']}\n"
            )

        elif item.get("debut"):

            response += f"- {item_type}"

            if semester:
                response += f" ({semester})"

            response += (
                f" : du {item['debut']}"
            )

            if item.get("fin"):
                response += (
                    f" au {item['fin']}"
                )

            response += "\n"

    return response.strip()

def get_formations():
    data = load_calendar()
    formations = data.get("formations", [])

    if not formations:
        return None

    return formations


# ============================================================
# Recherche dans les données officielles du projet ESIC
# ============================================================

import json
import re
import unicodedata
from pathlib import Path
from functools import lru_cache


# Le projet a pour structure :
# assistant_virtuel_educatif/
#   data/
#   backend/
#     app/
#       services/
#
# parents[3] correspond à la racine du projet depuis ce fichier.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OFFICIAL_DATA_DIR = PROJECT_ROOT / "data"


OFFICIAL_JSON_FILES = {
    "faq": "faq_complete.json",
    "procedures": "procedures_esic.json",
    "contacts": "annuaire_contacts.json",
    "timetable": "emploi_du_temps.json",
}


def normalize_search_text(value):
    """Normalise le texte pour faciliter la recherche."""
    if value is None:
        return ""

    value = str(value).lower().strip()
    value = unicodedata.normalize("NFD", value)
    value = "".join(
        char for char in value
        if unicodedata.category(char) != "Mn"
    )
    value = re.sub(r"[^a-z0-9\s'-]", " ", value)
    return " ".join(value.split())


@lru_cache(maxsize=16)
def load_official_json(filename):
    """
    Charge un JSON depuis le dossier data/.
    Le résultat est mis en cache pour éviter de relire
    le fichier à chaque question.
    """
    path = OFFICIAL_DATA_DIR / filename

    if not path.is_file():
        print(f"[ESIC DATA] Fichier introuvable : {path}")
        return None

    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)

        print(f"[ESIC DATA] Fichier chargé : {filename}")
        return data

    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        print(f"[ESIC DATA] Erreur de lecture de {filename} : {exc}")
        return None


def _collect_text_fields(value, path=""):
    """
    Transforme récursivement un objet JSON en champs textuels.
    Cela fonctionne avec des dictionnaires, des listes et
    différentes structures de données.
    """
    fields = []

    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            fields.extend(_collect_text_fields(item, child_path))

    elif isinstance(value, list):
        for index, item in enumerate(value):
            fields.extend(
                _collect_text_fields(item, f"{path}[{index}]")
            )

    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = str(value).strip()
        if text:
            fields.append((path, text))

    return fields


def _record_search_text(record):
    """Construit le texte indexable d'un enregistrement."""
    return " ".join(
        value for _, value in _collect_text_fields(record)
    )


def search_official_data(source, question, limit=5):
    """
    Recherche les enregistrements les plus pertinents
    dans une source officielle.

    source : 'faq', 'procedures', 'contacts' ou 'timetable'
    question : question de l'étudiant
    limit : nombre maximal de résultats
    """
    filename = OFFICIAL_JSON_FILES.get(source)

    if filename is None:
        return []

    data = load_official_json(filename)

    if data is None:
        return []

    query = normalize_search_text(question)
    query_tokens = set(query.split())

    if not query_tokens:
        return []

    # Les formats JSON peuvent être une liste directe
    # ou un dictionnaire contenant une liste d'éléments.
    if isinstance(data, list):
        records = data

    elif isinstance(data, dict):
        records = None

        for key in (
            "questions",
            "faq",
            "procedures",
            "contacts",
            "formations",
            "cours",
            "creneaux",
            "emploi_du_temps",
            "data",
            "items",
        ):
            candidate = data.get(key)

            if isinstance(candidate, list):
                records = candidate
                break

        # Un dictionnaire unique reste exploitable comme entrée.
        if records is None:
            records = [data]

    else:
        return []

    scored_results = []

    for record in records:
        if not isinstance(record, (dict, list, str)):
            continue

        fields = _collect_text_fields(record)
        searchable_text = normalize_search_text(
            " ".join(value for _, value in fields)
        )
        record_tokens = set(searchable_text.split())

        if not record_tokens:
            continue

        # Score simple : couverture des mots de la question,
        # complétée par une petite prime si la question entière
        # apparaît dans l'enregistrement.
        matched_tokens = query_tokens & record_tokens
        score = len(matched_tokens) / len(query_tokens)

        if len(query) >= 5 and query in searchable_text:
            score += 0.5

        if score > 0:
            scored_results.append({
                "source": source,
                "score": round(score, 3),
                "record": record,
            })

    scored_results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return scored_results[:max(1, limit)]


def get_official_data_status():
    """
    Indique quels fichiers officiels sont présents et lisibles.
    Utile pour vérifier la configuration sans afficher
    les coordonnées personnelles de l'annuaire.
    """
    status = {}

    for source, filename in OFFICIAL_JSON_FILES.items():
        path = OFFICIAL_DATA_DIR / filename
        data = load_official_json(filename) if path.is_file() else None

        status[source] = {
            "file": filename,
            "exists": path.is_file(),
            "loaded": data is not None,
        }

    return status
