from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import csv
import json
import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="Chatbot Campus API",
    version="2.1.0",
    description="Chatbot Campus ESIC avec base de connaissances projet.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CHEMINS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "chatbot.db"


# =========================================================
# UTILITAIRES TEXTE
# =========================================================

STOPWORDS = {
    "a", "à", "au", "aux", "avec", "ce", "ces", "dans", "de", "des",
    "du", "en", "et", "est", "il", "je", "la", "le", "les", "ma", "mes",
    "mon", "ou", "par", "pour", "que", "quel", "quelle", "quelles", "quels",
    "qui", "se", "sur", "un", "une", "vos", "votre", "comment", "où",
    "y", "d", "l", "m", "me", "te", "tu", "vous", "ton", "son", "sont",
    "puis", "faire", "obtenir", "du", "des", "est",
}


def normalize_text(value: object) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s@._/-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(value: object) -> list[str]:
    words = normalize_text(value).split()
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def similarity(query: str, candidate: str) -> float:
    q_tokens = set(tokenize(query))
    c_tokens = set(tokenize(candidate))

    if not q_tokens or not c_tokens:
        return 0.0

    overlap = len(q_tokens & c_tokens) / len(q_tokens)
    sequence = SequenceMatcher(
        None,
        normalize_text(query),
        normalize_text(candidate),
    ).ratio()

    return (overlap * 0.72) + (sequence * 0.28)


# =========================================================
# CHARGEMENT DES DATASETS
# =========================================================

knowledge_base: list[dict] = []
faq_items: list[dict] = []
contacts_data: dict = {}
schedule_data: dict = {}
procedures_data: dict = {}
pdf_chunks: list[dict] = []
load_errors: list[str] = []


def load_json_file(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(path)

    text = path.read_text(encoding="utf-8")

    # Réparation en mémoire de la petite anomalie structurelle du FAQ.
    if filename == "faq_complete.json":
        text = text.replace(
            '\n    }\n  ],\n    {\n      "id": "services_campus"',
            '\n    },\n    {\n      "id": "services_campus"',
            1,
        )

    return json.loads(text)


def add_kb_entry(
    source: str,
    title: str,
    content: str,
    category: str = "general",
    metadata: dict | None = None,
):
    if not content:
        return

    knowledge_base.append(
        {
            "source": source,
            "title": title,
            "content": content,
            "category": category,
            "metadata": metadata or {},
            "search_text": f"{title} {category} {content}",
        }
    )


def load_faq():
    global faq_items

    data = load_json_file("faq_complete.json")

    for category in data.get("categories", []):
        category_id = category.get("id", "general")
        category_name = category.get("nom", category_id)

        for item in category.get("questions", []):
            faq = {
                "id": item.get("id"),
                "question": item.get("question", ""),
                "answer": item.get("reponse", ""),
                "tags": item.get("tags", []),
                "frequency": item.get("frequence", ""),
                "category": category_name,
                "category_id": category_id,
            }
            faq_items.append(faq)

            add_kb_entry(
                source="FAQ",
                title=faq["question"],
                content=(
                    f"{faq['question']} "
                    f"{' '.join(faq['tags'])} "
                    f"{faq['answer']}"
                ),
                category=category_name,
                metadata=faq,
            )


def flatten_value(value: object, prefix: str = "") -> list[str]:
    parts: list[str] = []

    if isinstance(value, dict):
        for key, val in value.items():
            new_prefix = f"{prefix} {key}".strip()
            parts.extend(flatten_value(val, new_prefix))
    elif isinstance(value, list):
        for val in value:
            parts.extend(flatten_value(val, prefix))
    else:
        parts.append(f"{prefix} {value}".strip())

    return parts


def load_contacts():
    global contacts_data

    contacts_data = load_json_file("annuaire_contacts.json")

    metadata = contacts_data.get("metadata", {})
    add_kb_entry(
        source="Annuaire",
        title="Informations générales ESIC",
        content=" ".join(flatten_value(metadata)),
        category="contact",
    )

    for section_name, value in contacts_data.items():
        if section_name == "metadata":
            continue

        if isinstance(value, dict):
            text = " ".join(flatten_value(value, section_name))
            add_kb_entry(
                source="Annuaire",
                title=section_name.replace("_", " ").title(),
                content=text,
                category="contact",
            )
            continue

        if isinstance(value, list):
            for item in value:
                title = " ".join(
                    str(item.get(k, ""))
                    for k in [
                        "service",
                        "formation",
                        "nom",
                        "prenom",
                        "fonction",
                        "organisme",
                    ]
                    if isinstance(item, dict) and item.get(k)
                ) or section_name.replace("_", " ")

                text = " ".join(flatten_value(item, section_name))
                add_kb_entry(
                    source="Annuaire",
                    title=title,
                    content=text,
                    category="contact",
                    metadata={"section": section_name, "item": item},
                )


def load_schedule():
    global schedule_data

    schedule_data = load_json_file("emploi_du_temps.json")

    for formation in schedule_data.get("formations", []):
        add_kb_entry(
            source="Emploi du temps",
            title=formation.get("nom", formation.get("code", "Formation")),
            content=" ".join(flatten_value(formation)),
            category="planning",
            metadata=formation,
        )

    for group_schedule in schedule_data.get("emploi_du_temps", []):
        title = (
            f"Planning {group_schedule.get('formation')} "
            f"{group_schedule.get('groupe')}"
        )
        content = " ".join(flatten_value(group_schedule))
        add_kb_entry(
            source="Emploi du temps",
            title=title,
            content=content,
            category="planning",
            metadata=group_schedule,
        )

    for exam in schedule_data.get("examens", []):
        add_kb_entry(
            source="Calendrier examens",
            title=(
                f"Examens {exam.get('formation')} "
                f"{exam.get('semestre')}"
            ),
            content=" ".join(flatten_value(exam)),
            category="examens",
            metadata=exam,
        )

    for date in schedule_data.get("dates_importantes", []):
        add_kb_entry(
            source="Dates importantes",
            title=str(date.get("evenement", "Date importante")),
            content=" ".join(flatten_value(date)),
            category="calendrier",
            metadata=date,
        )


def load_csv_schedule():
    # Le fichier a été renommé sans accent dans le projet.
    possible_files = [
        DATA_DIR / "emploi_du_temps.csv",
        DATA_DIR / "emploi_du_temps_exclusive.csv",
    ]

    path = next((p for p in possible_files if p.exists()), None)
    if path is None:
        return

    try:
        text = path.read_text(encoding="cp1252")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin1")

    rows = list(csv.reader(text.splitlines(), delimiter=","))
    if len(rows) < 2:
        return

    header_index = None
    for i, row in enumerate(rows[:10]):
        if row and "formation" in normalize_text(row[0]):
            header_index = i
            break

    if header_index is None:
        return

    headers = [normalize_text(h).replace(" ", "_") for h in rows[header_index]]

    for row in rows[header_index + 1 :]:
        item = {}
        for index, header in enumerate(headers):
            if index < len(row):
                item[header] = row[index].strip()

        if not item.get("formation") or not item.get("groupe"):
            continue

        add_kb_entry(
            source="Emploi du temps CSV",
            title=f"Planning {item.get('formation')} {item.get('groupe')}",
            content=" ".join(f"{k} {v}" for k, v in item.items()),
            category="planning",
            metadata=item,
        )


def load_procedures():
    global procedures_data

    procedures_data = load_json_file("procedures_esic.json")

    for procedure in procedures_data.get("procedures", []):
        pieces = [
            procedure.get("titre", ""),
            procedure.get("description", ""),
            procedure.get("categorie", ""),
            procedure.get("periode", ""),
            procedure.get("duree_estimee", ""),
            procedure.get("delais", ""),
            procedure.get("cout", ""),
        ]
        pieces.extend(flatten_value(procedure.get("prerequis", [])))
        pieces.extend(flatten_value(procedure.get("documents_necessaires", [])))
        pieces.extend(flatten_value(procedure.get("etapes", [])))
        pieces.extend(flatten_value(procedure.get("faq", [])))
        pieces.extend(flatten_value(procedure.get("contacts", [])))

        add_kb_entry(
            source="Procédure ESIC",
            title=procedure.get("titre", procedure.get("id", "Procédure")),
            content=" ".join(str(piece) for piece in pieces if piece),
            category=procedure.get("categorie", "procedure"),
            metadata=procedure,
        )


def extract_pdf_chunks(filename: str, source: str, category: str):
    path = DATA_DIR / filename

    if not path.exists():
        return

    if PdfReader is None:
        load_errors.append(
            f"PDF non indexé ({filename}) : pypdf n'est pas installé."
        )
        return

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        load_errors.append(f"Impossible de lire {filename}: {exc}")
        return

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue

        chunk_size = 1800
        for start in range(0, len(text), chunk_size):
            chunk = text[start : start + chunk_size]
            metadata = {"file": filename, "page": page_number}

            entry = {
                "source": source,
                "title": f"{source} - page {page_number}",
                "content": chunk,
                "category": category,
                "metadata": metadata,
                "search_text": f"{source} {chunk}",
            }

            pdf_chunks.append(entry)
            knowledge_base.append(entry)


def load_all_datasets():
    knowledge_base.clear()
    faq_items.clear()
    pdf_chunks.clear()
    load_errors.clear()

    loaders = [
        ("faq_complete.json", load_faq),
        ("annuaire_contacts.json", load_contacts),
        ("emploi_du_temps.json", load_schedule),
        ("procedures_esic.json", load_procedures),
    ]

    for filename, loader in loaders:
        try:
            loader()
        except Exception as exc:
            load_errors.append(f"Erreur chargement {filename}: {exc}")

    try:
        load_csv_schedule()
    except Exception as exc:
        load_errors.append(f"Erreur chargement CSV emploi du temps: {exc}")

    extract_pdf_chunks(
        "guide_etudiant.pdf",
        "Guide de l'étudiant",
        "guide",
    )
    extract_pdf_chunks(
        "reglement_campus.pdf",
        "Règlement intérieur",
        "reglement",
    )
    extract_pdf_chunks(
        "procedures_esic.pdf",
        "Procédures administratives et académiques",
        "procedure",
    )
    extract_pdf_chunks(
        "donnees_utiles_projet.pdf",
        "Données utiles du projet",
        "documentation",
    )


load_all_datasets()


# =========================================================
# DETECTION STRUCTUREE : PLANNING
# =========================================================


def detect_day(query: str) -> str | None:
    normalized = normalize_text(query)
    mapping = {
        "lundi": "Lundi",
        "mardi": "Mardi",
        "mercredi": "Mercredi",
        "jeudi": "Jeudi",
        "vendredi": "Vendredi",
        "samedi": "Samedi",
        "dimanche": "Dimanche",
    }

    for key, value in mapping.items():
        if re.search(rf"\b{re.escape(key)}\b", normalized):
            return value
    return None


def detect_group(query: str) -> str | None:
    q = normalize_text(query).upper()

    groups: list[str] = []
    for formation in schedule_data.get("formations", []):
        groups.extend(formation.get("groupes", []))

    for group_schedule in schedule_data.get("emploi_du_temps", []):
        if group_schedule.get("groupe"):
            groups.append(str(group_schedule["groupe"]))

    for entry in knowledge_base:
        if entry.get("category") != "planning":
            continue
        metadata = entry.get("metadata") or {}
        group = metadata.get("groupe")
        if group:
            groups.append(str(group))

    for group in sorted(set(groups), key=len, reverse=True):
        if normalize_text(group).upper() in q:
            return group

    for formation in schedule_data.get("formations", []):
        code = normalize_text(formation.get("code", "")).upper()
        if code and code in q:
            return formation.get("code")

    return None


def answer_schedule(query: str) -> str | None:
    normalized = normalize_text(query)
    day = detect_day(query)
    group = detect_group(query)

    if not any(word in normalized for word in [
        "cours",
        "planning",
        "emploi du temps",
        "enseignant",
        "enseigne",
        "salle",
        "quel cours",
        "horaire",
    ]):
        return None

    if (
        any(word in normalized for word in [
            "cours",
            "planning",
            "emploi du temps",
        ])
        and group is None
        and day is not None
    ):
        return (
            "Pour afficher les cours, précisez votre groupe. "
            "Exemples disponibles dans le dataset : "
            "B1-A, B3-DATA-1, M1-IA-1 ou B3-CYBER-1."
        )

    if group is None:
        return None

    matching_schedules = [
        item
        for item in schedule_data.get("emploi_du_temps", [])
        if item.get("groupe") == group or item.get("formation") == group
    ]

    if not matching_schedules:
        return None

    schedule = matching_schedules[0]
    courses = schedule.get("cours", [])

    if day:
        courses = [course for course in courses if course.get("jour") == day]

    if not courses:
        return (
            f"Aucun créneau correspondant n'a été trouvé pour {group}"
            + (f" le {day}." if day else ".")
        )

    if "qui enseigne" in normalized or "enseignant" in normalized:
        subject_terms = set(tokenize(query))
        matches = []

        for course in courses:
            subject = course.get("matiere_nom", "")
            if subject_terms & set(tokenize(subject)):
                matches.append(course)

        if matches:
            lines = []
            for course in matches[:5]:
                lines.append(
                    f"- {course.get('matiere_nom')} : "
                    f"{course.get('enseignant_nom')} "
                    f"({course.get('jour')} "
                    f"{course.get('heure_debut')}-{course.get('heure_fin')})"
                )
            return "Voici les enseignements correspondants :\n" + "\n".join(lines)

    if (
        "salle" in normalized
        or "ou se trouve" in normalized
        or "où est" in normalized
    ):
        subject_terms = set(tokenize(query))
        matches = []

        for course in courses:
            subject = course.get("matiere_nom", "")
            if subject_terms & set(tokenize(subject)):
                matches.append(course)

        if matches:
            course = matches[0]
            return (
                f"Le cours {course.get('matiere_nom')} a lieu en "
                f"{course.get('salle_nom')} ({course.get('salle')}), "
                f"le {course.get('jour')} de {course.get('heure_debut')} "
                f"à {course.get('heure_fin')}."
            )

    lines = [
        f"{course.get('heure_debut')}–{course.get('heure_fin')} : "
        f"{course.get('matiere_nom')} ({course.get('type')}) — "
        f"{course.get('salle_nom')} — {course.get('enseignant_nom')}"
        for course in courses
    ]

    label = f"le {day}" if day else "dans ce planning"
    return (
        f"Pour {group}, voici les cours {label} :\n"
        + "\n".join(f"- {line}" for line in lines)
    )


# =========================================================
# US-006 : HORAIRES DES SERVICES
# =========================================================


def _service_hours_answer(service: dict) -> str:
    service_name = service.get("service", "Service")
    lines = [f"Horaires — {service_name}"]

    for key, value in service.items():
        if key in {"service", "responsable", "bureau", "batiment", "missions", "equipe"}:
            continue
        if value is None or value == "":
            continue

        label_map = {
            "horaires": "Horaires",
            "horaires_examens": "Horaires examens",
            "horaires_rdv": "Horaires rendez-vous",
        }
        label = label_map.get(key, key.replace("_", " ").capitalize())
        lines.append(f"{label} : {value}")

    return "\n".join(lines)


def answer_horaires(question: str) -> str | None:
    normalized = normalize_text(question)

    if not any(word in normalized for word in [
        "horaire",
        "horaires",
        "ouverture",
        "ouvre",
        "ouvert",
        "ferme",
        "fermeture",
        "heure",
        "heures",
    ]):
        return None

    services = contacts_data.get("horaires_services", {})
    if not services:
        return None

    aliases = {
        "accueil_general": [
            "accueil",
            "accueil general",
            "reception",
        ],
        "scolarite": [
            "scolarite",
        ],
        "bibliotheque": [
            "bibliotheque",
            "mediatheque",
        ],
        "restaurant_universitaire": [
            "restaurant universitaire",
            "restaurant u",
            "restaurant",
            "ru",
        ],
        "cafeteria": [
            "cafeteria",
        ],
        "salle_musculation": [
            "salle de sport",
            "salle de musculation",
            "musculation",
            "sport",
        ],
        "infirmerie": [
            "infirmerie",
            "infirmiere",
            "service sante",
            "sante",
        ],
        "helpdesk_informatique": [
            "helpdesk",
            "informatique",
            "support informatique",
            "support it",
            "support technique",
        ],
    }

    for service_key, service_aliases in aliases.items():
        if service_key not in services:
            continue

        if any(alias in normalized for alias in service_aliases):
            service = services[service_key]

            if isinstance(service, dict):
                return _service_hours_answer(service)

            return (
                f"Horaires — {service_key.replace('_', ' ').title()}\n"
                f"{service}"
            )

    lines = ["Horaires des services :"]

    for service_key, service in services.items():
        display_name = service_key.replace("_", " ").title()

        if isinstance(service, dict):
            display_name = service.get("service", display_name)
            hours = service.get("horaires", service.get("horaires_services", ""))

            if hours:
                lines.append(f"- {display_name} : {hours}")
            else:
                detail_lines = []
                for key, value in service.items():
                    if "horaire" in key and value:
                        detail_lines.append(str(value))
                if detail_lines:
                    lines.append(f"- {display_name} : " + " / ".join(detail_lines))
        else:
            lines.append(f"- {display_name} : {service}")

    return "\n".join(lines)


# =========================================================
# US-007 : CONTACTS DE LA SCOLARITE
# =========================================================


def answer_scolarite_contact(question: str) -> str | None:
    normalized = normalize_text(question)

    scolarite_keywords = [
        "scolarite",
        "service scolarite",
        "bureau scolarite",
    ]

    contact_keywords = [
        "contact",
        "contacter",
        "coordonnees",
        "email",
        "mail",
        "telephone",
        "tel",
        "numero",
        "adresse",
        "bureau",
        "ou se trouve",
        "ou est",
        "localisation",
        "situe",
        "trouver",
        "joindre",
    ]

    has_scolarite = any(keyword in normalized for keyword in scolarite_keywords)
    has_contact_request = any(keyword in normalized for keyword in contact_keywords)

    if not (has_scolarite and has_contact_request):
        return None

    services = contacts_data.get("services_administratifs", [])

    for service in services:
        service_name = normalize_text(service.get("service", ""))

        if service_name != "scolarite":
            continue

        responsable = service.get("responsable", {})

        return (
            "Scolarité\n"
            f"Responsable : {responsable.get('prenom', '')} "
            f"{responsable.get('nom', '')}\n"
            f"Email : {responsable.get('email', 'Non renseigné')}\n"
            f"Téléphone : {responsable.get('telephone', 'Non renseigné')}\n"
            f"Bureau : {service.get('bureau', 'Non renseigné')}\n"
            f"Bâtiment : {service.get('batiment', 'Non renseigné')}\n"
            f"Horaires : {service.get('horaires', 'Non renseignés')}\n"
            f"Adresse postale : {service.get('adresse', 'Non renseignée')}"
        )

    return None


# =========================================================
# US-008 : REGLES DE VIE DU CAMPUS
# =========================================================


def answer_reglement(question: str) -> str | None:
    """
    Répond aux questions concernant les règles de vie du campus.

    Les informations viennent du règlement intérieur chargé dans la base
    documentaire sous la catégorie "reglement".
    """
    normalized = normalize_text(question)

    # Détection de l'intention règlement / vie du campus.
    regulation_triggers = [
        "reglement",
        "regles",
        "regle de vie",
        "regles de vie",
        "vie du campus",
        "vie etudiante",
        "discipline",
        "sanction",
        "sanctions",
        "droit etudiant",
        "droits etudiant",
        "droits des etudiants",
        "devoir etudiant",
        "devoirs etudiant",
        "devoirs des etudiants",
        "interdit",
        "interdiction",
        "obligation",
        "obligatoire",
        "comportement",
        "respect des personnes",
        "respect des locaux",
        "securite",
        "fumer",
        "tabac",
        "alcool",
        "drogue",
        "harcelement",
        "violence",
        "fraude",
        "plagiat",
        "affichage",
        "affiche",
        "poster",
        "publication",
        "casque",
        "ecouteurs",
        "carte etudiante",
        "assurance responsabilite civile",
    ]

    if not any(trigger in normalized for trigger in regulation_triggers):
        return None

    # -----------------------------------------------------
    # ASSIDUITE / ABSENCES / RETARDS
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "assiduite",
        "presence",
        "absence",
        "absences",
        "retard",
        "retards",
        "absent",
    ]):
        return (
            "📚 Assiduité et présence :\n\n"
            "- La présence à tous les enseignements (CM, TD, TP et projets) est obligatoire et contrôlée.\n"
            "- Une absence justifiée doit être signalée avant le cours si elle est prévisible, ou dans les 48h si elle est imprévisible.\n"
            "- Le justificatif original doit être remis au service scolarité sous 5 jours ouvrés.\n"
            "- Les absences injustifiées entraînent une progression de sanctions : avertissement, convocations, puis conséquences académiques selon le nombre d'absences.\n"
            "- Un retard de moins de 10 minutes est toléré avec l'autorisation de l'enseignant ; au-delà, l'étudiant peut être refusé en cours et compté absent."
        )

    # -----------------------------------------------------
    # FRAUDE / PLAGIAT / REGLES D'EXAMEN
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "fraude",
        "triche",
        "plagiat",
        "plagier",
        "examen",
        "examens",
        "copie",
        "telephone pendant examen",
    ]):
        return (
            "📚 Règles des examens et intégrité académique :\n\n"
            "Pendant une épreuve, l'étudiant doit :\n"
            "- Présenter sa carte d'étudiant et une pièce d'identité\n"
            "- Éteindre et ranger son téléphone portable\n"
            "- Ne communiquer qu'avec les surveillants\n"
            "- Rester assis jusqu'à la fin de l'épreuve\n"
            "- Remettre sa copie au surveillant\n\n"
            "Sont notamment considérés comme fraude ou tentative de fraude :\n"
            "- La copie sur un autre étudiant ou un document non autorisé\n"
            "- La communication avec un autre candidat\n"
            "- La possession d'un téléphone ou objet électronique allumé\n"
            "- La substitution d'identité\n"
            "- Le plagiat, c'est-à-dire l'utilisation de travaux externes sans citation appropriée\n\n"
            "Une fraude constatée peut entraîner un procès-verbal, une audition, le passage devant le conseil de discipline et au minimum la note de 0/20 à l'épreuve."
        )

    # -----------------------------------------------------
    # SANCTIONS / DISCIPLINE
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "sanction",
        "sanctions",
        "discipline",
        "punition",
        "faute",
        "fautes",
    ]):
        return (
            "⚖️ Discipline et sanctions :\n\n"
            "Les manquements au règlement sont classés en trois catégories.\n\n"
            "Fautes mineures :\n"
            "- Retards répétés\n"
            "- Absence injustifiée ponctuelle\n"
            "- Oubli de carte étudiante\n"
            "- Incivilités légères\n\n"
            "Fautes graves :\n"
            "- Fraude ou tentative de fraude aux examens\n"
            "- Absences injustifiées répétées (>8)\n"
            "- Dégradations matérielles volontaires\n"
            "- Comportement perturbateur en cours\n"
            "- Non-respect des consignes de sécurité\n\n"
            "Fautes très graves :\n"
            "- Fraude grave ou récidive\n"
            "- Violence physique ou verbale\n"
            "- Harcèlement moral, sexuel ou discriminatoire\n"
            "- Vol\n"
            "- Consommation ou trafic de substances illicites\n"
            "- Diffusion de contenus illicites ou diffamatoires\n\n"
            "Sanctions possibles : avertissement oral ou écrit, blâme, exclusion temporaire, exclusion de certains cours ou activités, travail d'intérêt général, note de 0/20 à une épreuve et, pour les cas les plus graves, exclusion définitive."
        )

    # -----------------------------------------------------
    # RESPECT / COMPORTEMENT
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "respect",
        "comportement",
        "incivilite",
        "incivilites",
        "discrimination",
        "harcelement",
        "violence",
        "insulte",
        "diffamation",
    ]):
        return (
            "🤝 Respect et comportement :\n\n"
            "Chaque étudiant doit adopter un comportement respectueux envers :\n"
            "- Le personnel enseignant et administratif\n"
            "- Les autres étudiants\n"
            "- Les intervenants extérieurs\n"
            "- Le personnel d'entretien et de sécurité\n\n"
            "Sont notamment interdits et passibles de sanctions :\n"
            "- Les propos ou actes discriminatoires\n"
            "- Le harcèlement moral ou sexuel\n"
            "- La violence physique ou verbale\n"
            "- La diffamation ou l'injure"
        )

    # -----------------------------------------------------
    # LOCAUX / MATERIEL / PROPRETE
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "locaux",
        "materiel",
        "proprete",
        "degradation",
        "degrader",
        "installations",
        "equipement",
    ]):
        return (
            "🏫 Respect des locaux et du matériel :\n\n"
            "- Maintenir la propreté des locaux et respecter le tri sélectif\n"
            "- Utiliser le matériel de manière responsable\n"
            "- Signaler toute dégradation constatée\n"
            "- Ne pas modifier les installations, notamment informatiques et électriques\n\n"
            "Toute dégradation volontaire entraîne le remboursement des réparations et une sanction disciplinaire."
        )

    # -----------------------------------------------------
    # TENUE / CASQUE / ECOUTEURS
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "tenue",
        "vetement",
        "vetements",
        "habillement",
        "casque",
        "ecouteurs",
        "dress code",
    ]):
        return (
            "👕 Tenue et équipements en cours :\n\n"
            "- Aucun code vestimentaire strict n'est imposé.\n"
            "- Une tenue décente et appropriée au contexte éducatif est requise.\n"
            "- Les vêtements comportant des inscriptions injurieuses ou discriminatoires sont interdits.\n"
            "- Les tenues manifestement indécentes sont interdites.\n"
            "- Le port du casque audio ou d'écouteurs en cours est interdit, sauf autorisation pédagogique."
        )

    # -----------------------------------------------------
    # TABAC / ALCOOL / SUBSTANCES
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "fumer",
        "tabac",
        "cigarette",
        "cigarettes",
        "vapotage",
        "alcool",
        "drogue",
        "substances",
    ]):
        return (
            "🚭 Tabac et substances :\n\n"
            "Il est strictement interdit de :\n"
            "- Fumer dans l'enceinte des bâtiments, y compris les cigarettes électroniques\n"
            "- Consommer de l'alcool dans les locaux, sauf lors d'événements autorisés\n"
            "- Détenir ou consommer des substances illicites\n\n"
            "Des espaces fumeurs extérieurs signalés doivent être utilisés exclusivement."
        )

    # -----------------------------------------------------
    # SECURITE
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "issue de secours",
        "evacuation",
        "alarme",
        "extincteur",
        "objet dangereux",
        "arme",
        "armes",
        "explosif",
        "explosifs",
        "securite",
    ]):
        return (
            "🛡️ Règles de sécurité :\n\n"
            "Chaque étudiant doit :\n"
            "- Respecter les consignes de sécurité affichées\n"
            "- Participer aux exercices d'évacuation incendie\n"
            "- Ne pas obstruer les issues de secours\n"
            "- Signaler tout incident ou danger\n\n"
            "Il est strictement interdit d'introduire des objets dangereux et de modifier les équipements de sécurité, notamment les alarmes et extincteurs."
        )

    # -----------------------------------------------------
    # AFFICHAGE / COMMUNICATION
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "affichage",
        "afficher",
        "affiche",
        "poster",
        "publication",
        "reseaux sociaux",
        "spam",
        "communication",
    ]):
        return (
            "📌 Affichage et communication :\n\n"
            "- L'affichage est autorisé uniquement sur les panneaux dédiés, après validation par le BVE.\n"
            "- Sont notamment acceptés : événements associatifs, offres de stages/emplois et petites annonces étudiantes.\n"
            "- L'affichage sauvage est retiré.\n\n"
            "Dans la communication numérique, sont notamment interdits le spam, les sollicitations commerciales, les propos offensants ou discriminatoires et le partage de contenus illicites."
        )

    # -----------------------------------------------------
    # DROITS / DEVOIRS / PRINCIPES GENERAUX
    # -----------------------------------------------------
    if any(word in normalized for word in [
        "droit",
        "droits",
        "devoir",
        "devoirs",
        "non discrimination",
        "discrimination",
        "laicite",
        "religion",
        "liberte",
    ]):
        return (
            "📖 Droits et devoirs des étudiants :\n\n"
            "Droits :\n"
            "- Liberté d'expression dans le respect des lois et du bon fonctionnement de l'établissement\n"
            "- Droit de réunion\n"
            "- Droit d'association\n"
            "- Droit de représentation\n"
            "- Droit à l'information\n\n"
            "Devoirs :\n"
            "- Respecter les personnes\n"
            "- Respecter les biens et les locaux\n"
            "- Adopter une tenue décente et appropriée\n"
            "- Respecter les règles concernant le tabac et les substances\n"
            "- Respecter les règles d'assiduité et d'intégrité académique"
        )

    # -----------------------------------------------------
    # QUESTION GENERALE : REGLES DE VIE
    # -----------------------------------------------------
    return (
        "📖 Règles de vie du campus :\n\n"
        "Le règlement intérieur définit les règles de fonctionnement de l'ESIC ainsi que les droits et obligations des étudiants.\n\n"
        "Les principaux thèmes sont :\n"
        "- Respect des personnes et lutte contre les discriminations\n"
        "- Respect des biens, des locaux et du matériel\n"
        "- Tenue et comportement\n"
        "- Assiduité, absences et retards\n"
        "- Règles des examens, fraude et plagiat\n"
        "- Sécurité, tabac, alcool et substances\n"
        "- Affichage et communication\n"
        "- Droits et devoirs des étudiants\n"
        "- Discipline, sanctions et recours\n\n"
        "Le règlement intérieur complet est disponible dans les documents du campus."
    )


# =========================================================
# US-009 : DATES IMPORTANTES DU CALENDRIER
# =========================================================


def _format_date(value: object) -> str:
    """Convertit YYYY-MM-DD en DD/MM/YYYY quand c'est possible."""
    raw = str(value or "").strip()

    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if match:
        year, month, day = match.groups()
        return f"{day}/{month}/{year}"

    return raw


def _calendar_event_line(item: dict) -> str:
    date_value = _format_date(item.get("date"))
    event = item.get("evenement", "Événement")
    event_type = item.get("type")

    if event_type:
        return f"- {date_value} : {event} ({event_type})"

    return f"- {date_value} : {event}"


def answer_calendrier(question: str) -> str | None:
    """Répond aux questions concernant les dates importantes du calendrier."""
    normalized = normalize_text(question)

    # Une question explicitement centrée sur le règlement doit rester gérée
    # par US-008, même si elle contient le mot "examen".
    regulation_words = [
        "reglement",
        "regle",
        "regles",
        "fraude",
        "triche",
        "plagiat",
        "sanction",
        "discipline",
    ]
    if any(word in normalized for word in regulation_words):
        return None

    # Mots-clés principaux du calendrier.
    direct_calendar_terms = [
        "calendrier",
        "date importante",
        "dates importantes",
        "rentree",
        "vacances",
        "rattrapage",
        "rattrapages",
        "semestre",
        "stage",
        "stages",
        "jour ferie",
        "jours feries",
        "echeance",
        "echeances",
    ]

    # Pour "examen(s)", on exige une formulation temporelle ou calendaire
    # afin de ne pas détourner les questions sur les règles d'examen.
    exam_calendar_question = (
        "examen" in normalized
        and any(word in normalized for word in [
            "quand",
            "date",
            "dates",
            "calendrier",
            "periode",
            "commence",
            "commencent",
            "fin",
            "debut",
        ])
    )

    if not any(term in normalized for term in direct_calendar_terms) and not exam_calendar_question:
        return None

    important_dates = schedule_data.get("dates_importantes", [])
    metadata = schedule_data.get("metadata", {})
    semesters = metadata.get("semestres", [])
    academic_year = metadata.get("annee_academique", "2024-2025")

    if not important_dates and not semesters:
        return None

    # -----------------------------------------------------
    # CALENDRIER COMPLET / DATES IMPORTANTES
    # -----------------------------------------------------
    if any(phrase in normalized for phrase in [
        "dates importantes",
        "date importante",
        "calendrier academique",
        "calendrier scolaire",
        "calendrier de l annee",
        "toutes les dates",
        "echeances importantes",
    ]):
        lines = [f"📅 Calendrier académique {academic_year} :"]

        if important_dates:
            lines.append("")
            lines.append("Dates importantes :")
            for item in important_dates:
                if isinstance(item, dict) and item.get("date"):
                    lines.append(_calendar_event_line(item))

        return "\n".join(lines)

    # -----------------------------------------------------
    # CATEGORIES PRECISES
    # -----------------------------------------------------
    selected_type = None

    if any(term in normalized for term in ["vacance", "vacances"]):
        selected_type = "Vacances"
    elif any(term in normalized for term in ["rattrapage", "rattrapages"]):
        selected_type = "Examens"
    elif "examen" in normalized:
        selected_type = "Examens"
    elif any(term in normalized for term in ["stage", "stages"]):
        selected_type = "Stage"
    elif "rentree" in normalized:
        selected_type = "Rentrée"

    if selected_type:
        matching = [
            item
            for item in important_dates
            if isinstance(item, dict)
            and normalize_text(item.get("type", "")) == normalize_text(selected_type)
        ]

        # Les rattrapages sont classés dans "Examens" dans le JSON.
        if selected_type == "Examens":
            if "rattrapage" in normalized:
                matching = [
                    item
                    for item in important_dates
                    if isinstance(item, dict)
                    and "rattrapage" in normalize_text(item.get("evenement", ""))
                ]

            if not matching:
                matching = [
                    item
                    for item in important_dates
                    if isinstance(item, dict)
                    and any(
                        token in normalize_text(item.get("evenement", ""))
                        for token in ["examen", "rattrapage"]
                    )
                ]

        if selected_type == "Rentrée" and not matching:
            matching = [
                item
                for item in important_dates
                if isinstance(item, dict)
                and "rentree" in normalize_text(item.get("evenement", ""))
            ]

        if matching:
            title = selected_type
            if selected_type == "Examens":
                title = "Examens et rattrapages"

            lines = [f"📅 {title} — {academic_year} :"]
            lines.extend(_calendar_event_line(item) for item in matching)
            return "\n".join(lines)

    # -----------------------------------------------------
    # SEMESTRES
    # -----------------------------------------------------
    if "semestre" in normalized and semesters:
        requested = None
        if re.search(r"\bs1\b|semestre 1", normalized):
            requested = "S1"
        elif re.search(r"\bs2\b|semestre 2", normalized):
            requested = "S2"

        candidates = semesters
        if requested:
            candidates = [
                semester
                for semester in semesters
                if normalize_text(semester.get("semestre", "")) == normalize_text(requested)
            ]

        if candidates:
            lines = [f"📅 Calendrier {academic_year} :"]
            for semester in candidates:
                name = semester.get("semestre", "Semestre")
                debut = _format_date(semester.get("debut"))
                fin = _format_date(semester.get("fin"))
                lines.append(f"- {name} : {debut} → {fin}")

                for vacation in semester.get("vacances", []):
                    if isinstance(vacation, dict):
                        lines.append(
                            f"  - Vacances {vacation.get('nom', '')} : "
                            f"{_format_date(vacation.get('debut'))} → "
                            f"{_format_date(vacation.get('fin'))}"
                        )

                exams = semester.get("examens")
                if isinstance(exams, dict):
                    lines.append(
                        f"  - Examens : {_format_date(exams.get('debut'))} → "
                        f"{_format_date(exams.get('fin'))}"
                    )

                stages = semester.get("stages")
                if isinstance(stages, dict):
                    lines.append(
                        f"  - Stages : {_format_date(stages.get('debut'))} → "
                        f"{_format_date(stages.get('fin'))}"
                    )

            return "\n".join(lines)

    # -----------------------------------------------------
    # EVENEMENT PRECIS
    # -----------------------------------------------------
    best = None
    best_score = 0.0

    for item in important_dates:
        if not isinstance(item, dict):
            continue

        event_text = " ".join([
            str(item.get("evenement", "")),
            str(item.get("type", "")),
            str(item.get("date", "")),
        ])
        score = similarity(question, event_text)

        if score > best_score:
            best_score = score
            best = item

    if best and best_score >= 0.34:
        return (
            f"📅 {best.get('evenement', 'Événement')} : "
            f"{_format_date(best.get('date'))} "
            f"({best.get('type', 'Date importante')})."
        )

    # -----------------------------------------------------
    # REPLI : CALENDRIER GENERAL
    # -----------------------------------------------------
    lines = [f"📅 Voici les principales dates du calendrier {academic_year} :"]
    for item in important_dates[:15]:
        if isinstance(item, dict) and item.get("date"):
            lines.append(_calendar_event_line(item))

    return "\n".join(lines)


# =========================================================
# CONTACTS GENERAUX
# =========================================================


def find_service_contact(query: str) -> str | None:
    normalized = normalize_text(query)

    service_aliases = {
        "scolarite": ["scolarite"],
        "admissions": ["admission", "admissions"],
        "bibliotheque": ["bibliotheque", "mediatheque"],
        "informatique": [
            "informatique",
            "helpdesk",
            "support it",
            "support informatique",
        ],
        "restaurant": [
            "restaurant universitaire",
            "restaurant",
            "ru",
            "cafeteria",
        ],
        "international": [
            "international",
            "relations internationales",
        ],
        "comptabilite": [
            "comptabilite",
            "finance",
        ],
    }

    requested_service = None

    for service, aliases in service_aliases.items():
        if any(normalize_text(alias) in normalized for alias in aliases):
            requested_service = service
            break

    if not requested_service:
        return None

    for item in contacts_data.get("services_administratifs", []):
        service_name = normalize_text(item.get("service", ""))

        if requested_service in service_name or (
            requested_service == "informatique"
            and "informatique" in service_name
        ):
            resp = item.get("responsable", {})
            return (
                f"{item.get('service')}\n"
                f"Responsable : {resp.get('prenom', '')} {resp.get('nom', '')}\n"
                f"Email : {resp.get('email', 'non renseigné')}\n"
                f"Téléphone : {resp.get('telephone', 'non renseigné')}\n"
                f"Bureau : {item.get('bureau', 'non renseigné')}\n"
                f"Horaires : {item.get('horaires', 'non renseignés')}"
            )

    for item in contacts_data.get("services_etudiants", []):
        service_name = normalize_text(item.get("service", ""))

        if requested_service in service_name or (
            requested_service == "bibliotheque"
            and "bibliotheque" in service_name
        ) or (
            requested_service == "restaurant"
            and (
                "restaurant" in service_name
                or "cafeteria" in service_name
            )
        ):
            resp = item.get("responsable", {})
            return (
                f"{item.get('service')}\n"
                f"Responsable : {resp.get('prenom', '')} {resp.get('nom', '')}\n"
                f"Email : {resp.get('email', 'non renseigné')}\n"
                f"Téléphone : {resp.get('telephone', 'non renseigné')}\n"
                f"Bureau : {item.get('bureau', 'non renseigné')}\n"
                f"Horaires : {item.get('horaires', 'non renseignés')}"
            )

    return None


# =========================================================
# US-004 / US-007 : FORMATIONS
# =========================================================


def answer_formations(question: str) -> str | None:
    normalized = normalize_text(question)

    formation_words = [
        "formation",
        "formations",
        "filiere",
        "filieres",
        "parcours",
        "cursus",
        "etude",
        "etudes",
        "programme",
        "programmes",
        "diplome",
        "diplomes",
        "master",
        "masters",
        "bachelor",
        "bachelors",
        "licence",
        "specialisation",
        "specialisations",
    ]

    if not any(word in normalized for word in formation_words):
        return None

    formations = schedule_data.get("formations", [])
    if not formations:
        return None

    # US-010 : catalogue des formations fourni par les documents du projet.
    # Le guide étudiant présente les spécialisations suivantes.
    guide_catalog = {
        "Bachelor (Bac+3)": [
            "Développement Informatique",
            "Cybersécurité et Réseaux",
            "Data Science et IA",
            "Digital Marketing",
            "Management de Projets IT",
        ],
        "Master (Bac+5)": [
            "Ingénierie Logicielle et DevOps",
            "Cybersécurité et Sécurité des SI",
            "Intelligence Artificielle et Big Data",
            "Transformation Digitale",
            "Management de l'Innovation",
            "Chief Product Officer",
        ],
    }

    # Question générale : le visiteur veut découvrir l'offre de formation.
    broad_words = [
        "quelles formations",
        "quels formations",
        "formation proposee",
        "formations proposees",
        "formation disponibles",
        "formations disponibles",
        "quelles filieres",
        "quels parcours",
        "quelles etudes",
        "quels cursus",
        "quels diplomes",
        "diplomes proposes",
        "diplomes prepares",
        "quels bachelors",
        "quels bachelors proposes",
        "bachelors proposes",
        "bachelors disponibles",
        "quels masters",
        "quels masters proposes",
        "masters proposes",
        "masters disponibles",
        "que propose",
        "catalogue des formations",
        "offre de formation",
        "offre de formations",
        "etudes proposees",
        "etudes disponibles",
        "programmes proposes",
        "programmes disponibles",
    ]

    # Questions ciblées sur le niveau demandé. Ces blocs doivent passer AVANT
    # la détection générale afin de ne pas retourner tout le catalogue.
    asks_bachelor = (
        any(term in normalized for term in ["bachelor", "bachelors", "bac+3", "bac 3", "bac3"])
        and "master" not in normalized
    )
    asks_master = (
        any(term in normalized for term in ["master", "masters", "bac+5", "bac 5", "bac5"])
        and "bachelor" not in normalized
    )

    if asks_bachelor:
        lines = ["🎓 Les formations Bachelor (Bac+3) proposées sont :"]
        for item in guide_catalog["Bachelor (Bac+3)"]:
            lines.append(f"- {item}")
        return "\n".join(lines)

    if asks_master:
        lines = ["🎓 Les formations Master (Bac+5) proposées sont :"]
        for item in guide_catalog["Master (Bac+5)"]:
            lines.append(f"- {item}")
        return "\n".join(lines)

    # Question générale : le visiteur veut découvrir l'ensemble de l'offre.
    if any(word in normalized for word in broad_words):
        lines = ["🎓 Voici les formations proposées dans les données du projet :", ""]

        lines.append("Bachelor (Bac+3) :")
        for item in guide_catalog["Bachelor (Bac+3)"]:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("Master (Bac+5) :")
        for item in guide_catalog["Master (Bac+5)"]:
            lines.append(f"- {item}")

        return "\n".join(lines)

    # Questions ciblées sur le Bachelor 3.
    if (
        ("bachelor 3" in normalized or "b3" in normalized)
        and any(word in normalized for word in ["specialisation", "specialisations", "parcours", "formation"])
    ):
        return (
            "🎓 Le Bachelor 3 propose 5 spécialisations :\n"
            "- Développement & Ingénierie Logicielle\n"
            "- Cybersécurité\n"
            "- Data Science & IA\n"
            "- Digital Marketing\n"
            "- Product Management"
        )

    # Questions ciblées sur les Masters.
    if "master" in normalized and any(
        word in normalized
        for word in ["quels", "quelles", "specialisation", "specialisations", "parcours", "formations"]
    ):
        lines = ["🎓 Les spécialisations de Master (Bac+5) sont :"]
        for item in guide_catalog["Master (Bac+5)"]:
            lines.append(f"- {item}")
        return "\n".join(lines)

    # Formation explicitement demandée : recherche dans emploi_du_temps.json.
    best = None
    best_score = 0.0

    for formation in formations:
        searchable = " ".join(flatten_value(formation))
        score = similarity(question, searchable)
        if score > best_score:
            best_score = score
            best = formation

    if not best or best_score < 0.25:
        return None

    lines = [
        f"{best.get('code', '')} — {best.get('nom', 'Formation')}",
    ]

    for key in [
        "niveau",
        "duree",
        "description",
        "rythme",
        "modalite",
        "specialisations",
        "groupes",
    ]:
        value = best.get(key)
        if value:
            if isinstance(value, list):
                value = ", ".join(map(str, value))
            label = key.replace("_", " ").capitalize()
            lines.append(f"{label} : {value}")

    return "\n".join(lines)


# =========================================================
# PROCEDURES
# =========================================================


def answer_procedure(query: str) -> str | None:
    normalized = normalize_text(query)

    if not any(word in normalized for word in [
        "procedure",
        "demarche",
        "comment",
        "obtenir",
        "faire une demande",
        "inscription",
        "certificat",
        "absence",
        "stage",
        "alternance",
        "bourse",
    ]):
        return None

    best = None
    best_score = 0.0

    for procedure in procedures_data.get("procedures", []):
        candidate = " ".join([
            str(procedure.get("titre", "")),
            str(procedure.get("description", "")),
            str(procedure.get("categorie", "")),
            " ".join(flatten_value(procedure.get("faq", []))),
        ])
        score = similarity(query, candidate)

        if score > best_score:
            best_score = score
            best = procedure

    if not best or best_score < 0.22:
        return None

    lines = [
        f"📌 {best.get('titre', 'Procédure ESIC')}",
        "",
        str(best.get("description", "")),
    ]

    if best.get("prerequis"):
        lines.extend(["", "Prérequis :"])
        lines.extend(f"- {x}" for x in best["prerequis"])

    if best.get("documents_necessaires"):
        lines.extend(["", "Documents nécessaires :"])
        lines.extend(f"- {x}" for x in best["documents_necessaires"])

    if best.get("etapes"):
        lines.extend(["", "Étapes :"])
        for step in best["etapes"]:
            if isinstance(step, dict):
                numero = step.get("numero", "")
                titre = step.get("titre", "")
                description = step.get("description", "")
                lines.append(f"{numero}. {titre} : {description}")
            else:
                lines.append(f"- {step}")

    if best.get("delais"):
        lines.extend(["", f"Délais : {best['delais']}"])

    if best.get("cout"):
        lines.append(f"Coût : {best['cout']}")

    if best.get("contacts"):
        lines.append("")
        lines.append("Contact :")
        for contact in best["contacts"]:
            if isinstance(contact, dict):
                lines.append(
                    f"- {contact.get('service', '')} | "
                    f"{contact.get('email', '')} | "
                    f"{contact.get('telephone', '')}"
                )
            else:
                lines.append(f"- {contact}")

    return "\n".join(lines)


# =========================================================
# RECHERCHE FAQ / BASE DOCUMENTAIRE
# =========================================================


def answer_from_faq(query: str) -> str | None:
    best_item = None
    best_score = 0.0

    for item in faq_items:
        searchable = " ".join([
            item.get("question", ""),
            " ".join(item.get("tags", [])),
            item.get("category", ""),
        ])

        score = similarity(query, searchable)
        question_score = similarity(query, item.get("question", ""))
        score = (score * 0.45) + (question_score * 0.55)

        if score > best_score:
            best_score = score
            best_item = item

    if not best_item or best_score < 0.38:
        return None

    return best_item.get("answer", "")


def answer_from_documents(query: str) -> str | None:
    best = None
    best_score = 0.0

    for entry in knowledge_base:
        if entry.get("source") == "Données utiles du projet":
            continue

        score = similarity(query, entry.get("search_text", ""))

        if entry.get("source") in [
            "Annuaire",
            "Emploi du temps",
            "Procédure ESIC",
            "Règlement intérieur",
            "Guide de l'étudiant",
        ]:
            score += 0.03

        if score > best_score:
            best_score = score
            best = entry

    if not best or best_score < 0.28:
        return None

    content = best.get("content", "").strip()
    if not content:
        return None

    if len(content) > 1400:
        content = content[:1400].rstrip() + "..."

    return content


# =========================================================
# REPONSE PRINCIPALE
# =========================================================


def generate_answer(
    question: str,
    current_topic: str | None = None,
) -> tuple[str, str]:
    normalized = normalize_text(question)

    # Salutations
    if normalized in {
        "bonjour",
        "salut",
        "hello",
        "bonsoir",
        "coucou",
    }:
        return "Bonjour 👋 Comment puis-je vous aider ?", "salutation"

    # US-007 : très ciblé et AVANT la recherche FAQ/documentaire.
    scolarite_contact = answer_scolarite_contact(question)
    if scolarite_contact:
        return scolarite_contact, "contact"

    # US-006 : horaires des services.
    horaires = answer_horaires(question)
    if horaires:
        return horaires, "horaires"

    # Contacts généraux.
    contact = find_service_contact(question)
    if contact and any(
        word in normalized
        for word in [
            "contact",
            "email",
            "mail",
            "telephone",
            "joindre",
            "contacter",
            "responsable",
        ]
    ):
        return contact, "contact"

    # US-009 : dates importantes du calendrier.
    calendrier = answer_calendrier(question)
    if calendrier:
        return calendrier, "calendrier"

    # US-008 : règlement intérieur AVANT la FAQ pour éviter les mauvais matchs.
    reglement = answer_reglement(question)
    if reglement:
        return reglement, "reglement"

    # Formations structurées : AVANT la FAQ pour éviter les mauvais matchs.
    formation = answer_formations(question)
    if formation:
        return formation, "formation"

    # Planning structuré.
    schedule = answer_schedule(question)
    if schedule:
        return schedule, "planning"

    # FAQ exacte / proche.
    faq = answer_from_faq(question)
    if faq:
        return faq, "faq"

    # Procédures structurées.
    procedure = answer_procedure(question)
    if procedure:
        return procedure, "procedure"

    # Recherche documentaire.
    document_answer = answer_from_documents(question)
    if document_answer:
        return document_answer, "document"

    # Contexte actuel si disponible.
    if current_topic:
        return (
            f"Je n'ai pas trouvé de réponse précise dans la base de connaissances "
            f"pour ce nouveau message. Le contexte courant est « {current_topic} ». "
            "Pouvez-vous préciser votre demande ?"
        ), "fallback"

    return (
        "Je n'ai pas trouvé de réponse précise dans la base de connaissances. "
        "Essayez une question sur les horaires, la scolarité, les formations, "
        "les procédures, les contacts, le planning ou le règlement du campus."
    ), "fallback"


# =========================================================
# DETECTION DE SUJET
# =========================================================


def detecter_sujet(question: str) -> str:
    normalized = normalize_text(question)

    subjects = {
        "horaires": ["horaire", "horaires", "ouverture", "ouvert", "heure"],
        "scolarite": [
            "scolarite",
            "inscription",
            "certificat",
            "absence",
            "releve",
        ],
        "formations": [
            "formation",
            "formations",
            "master",
            "bachelor",
            "licence",
        ],
        "planning": [
            "cours",
            "planning",
            "emploi du temps",
            "salle",
            "enseignant",
        ],
        "calendrier": [
            "calendrier",
            "date",
            "dates",
            "vacances",
            "examen",
        ],
        "reglement": [
            "reglement",
            "regle",
            "regles",
            "sanction",
            "assiduite",
        ],
        "campus": [
            "campus",
            "bibliotheque",
            "cafeteria",
            "restaurant",
        ],
        "contact": [
            "contact",
            "contacter",
            "email",
            "telephone",
            "responsable",
        ],
        "procedure": [
            "procedure",
            "demarche",
            "comment obtenir",
            "demande",
        ],
    }

    # Priorité à la scolarité quand le mot est explicitement présent.
    if "scolarite" in normalized:
        return "scolarite"

    if any(word in normalized for word in subjects["horaires"]):
        return "horaires"

    for subject, words in subjects.items():
        if subject == "horaires":
            continue
        if any(word in normalized for word in words):
            return subject

    return "general"


# =========================================================
# BASE SQLITE
# =========================================================


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            context_version INTEGER NOT NULL DEFAULT 1,
            context_topic TEXT
        )
        """
    )

    cursor.execute("PRAGMA table_info(sessions)")
    session_columns = {row["name"] for row in cursor.fetchall()}

    if "context_version" not in session_columns:
        cursor.execute(
            "ALTER TABLE sessions ADD COLUMN context_version "
            "INTEGER NOT NULL DEFAULT 1"
        )

    if "context_topic" not in session_columns:
        cursor.execute(
            "ALTER TABLE sessions ADD COLUMN context_topic TEXT"
        )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            context_version INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id)
                REFERENCES sessions(session_id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute("PRAGMA table_info(messages)")
    message_columns = {row["name"] for row in cursor.fetchall()}

    if "context_version" not in message_columns:
        cursor.execute(
            "ALTER TABLE messages ADD COLUMN context_version "
            "INTEGER NOT NULL DEFAULT 1"
        )

    # =====================================================
    # US-011 : JOURNAL DES QUESTIONS
    # =====================================================
    # Une ligne est créée à chaque question reçue par l'API.
    # Le timestamp est enregistré en UTC directement par SQLite.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS question_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id)
                REFERENCES sessions(session_id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_question_logs_session_id "
        "ON question_logs(session_id)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_question_logs_timestamp "
        "ON question_logs(timestamp)"
    )

    # =====================================================
    # US-012 : JOURNAL DES EVENEMENTS DE SECURITE
    # =====================================================
    # Les tentatives d'injection bloquees sont conservees avec
    # leur session, leur question, la regle detectee et le timestamp.
    # La table n'a volontairement pas de cle etrangere vers sessions :
    # une tentative malveillante doit pouvoir etre journalisee meme
    # avec un session_id invalide ou inexistant.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            question TEXT NOT NULL,
            attack_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_security_logs_timestamp "
        "ON security_logs(timestamp)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_security_logs_session_id "
        "ON security_logs(session_id)"
    )

    # =====================================================
    # US-013 : JOURNAL DES DEPASSEMENTS DE RATE LIMIT
    # =====================================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            request_count INTEGER NOT NULL,
            limit_value INTEGER NOT NULL,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rate_limit_logs_session_id "
        "ON rate_limit_logs(session_id)"
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rate_limit_logs_timestamp "
        "ON rate_limit_logs(timestamp)"
    )

    connection.commit()
    connection.close()


init_db()


# =========================================================
# MODELES API
# =========================================================


class Question(BaseModel):
    question: str
    session_id: str


# =========================================================
# US-012 : FILTRE ANTI-INJECTION
# =========================================================

# Les motifs sont volontairement ciblés : l'objectif est de bloquer
# une tentative d'exécution, de manipulation des instructions ou de
# détournement du backend sans bloquer les questions campus normales.
INJECTION_RULES: list[tuple[str, str, str]] = [
    (
        "prompt_injection",
        "prompt_injection",
        r"\b(ignore|oublie|contourne|bypass|desactive|desactivez)\b.{0,120}\b(instruction|instructions|consigne|consignes|regle|regles|system prompt|prompt systeme)\b",
    ),
    (
        "prompt_extraction",
        "prompt_extraction",
        r"\b(donne|donner|affiche|afficher|montre|montrer|revele|reveler|show|reveal)\b.{0,100}\b(system prompt|prompt systeme|instructions internes|instructions cachees|secret systeme)\b",
    ),
    (
        "role_override",
        "role_override",
        r"\b(tu es maintenant|tu es desormais|tu es desormais|agis comme|joue le role de|act as|you are now|pretend to be)\b",
    ),
    (
        "jailbreak",
        "jailbreak",
        r"\b(jailbreak|dan mode|do anything now|developer mode|mode developpeur sans restriction)\b",
    ),
    (
        "sql_injection",
        "sql_injection",
        r"""(?:\b(union\s+(all\s+)?select|insert\s+into|update\s+\w+\s+set|delete\s+from|drop\s+(table|database)|alter\s+table|truncate\s+table|pragma\s+\w+)\b|['"]\s*or\s+['"]?\d+['"]?\s*=\s*['"]?\d+['"]?)""",
    ),
    (
        "code_execution",
        "code_execution",
        r"(?:__import__\s*\(|os\.(?:system|popen)\s*\(|subprocess\.(?:run|popen|call)\s*\(|(?:eval|exec)\s*\()",
    ),
    (
        "xss",
        "xss",
        r"(?:<\s*script\b|javascript\s*:|onerror\s*=|onload\s*=|onclick\s*=)",
    ),
    (
        "shell_command",
        "shell_command",
        r"(?:\b(?:powershell|pwsh)\b|\bcmd(?:\.exe)?\b\s+(?:-c|/c|/k)|\bbash\b\s+-c|\bsh\b\s+-c|\b(?:get|set|start|stop|invoke|remove|new|restart|stop)-[a-z][a-z0-9-]*\b|\brm\s+-rf\b|\bsudo\s+|\bshutdown\s+/|\bformat\s+[a-z]:)",
    ),
    (
        "path_traversal",
        "path_traversal",
        r"(?:\.\./){2,}|(?:\.\\){3,}",
    ),
]


def detect_injection(question: str) -> tuple[bool, str | None, str | None]:
    """
    Analyse une question et retourne :
    (bloquee, type_attaque, raison)
    """
    raw_question = str(question or "")
    normalized = normalize_text(raw_question)

    for rule_name, attack_type, pattern in INJECTION_RULES:
        # Les regex sont appliquees sur une version normalisee pour
        # les tentatives textuelles et sur le texte brut pour les
        # constructions HTML/JS sensibles.
        target = raw_question if attack_type in {"xss", "code_execution", "shell_command", "path_traversal", "sql_injection"} else normalized
        if re.search(pattern, target, flags=re.IGNORECASE | re.DOTALL):
            return True, attack_type, rule_name

    return False, None, None


def log_security_event(
    session_id: str | None,
    question: str,
    attack_type: str,
    reason: str,
) -> int:
    """Enregistre une tentative d'injection dans security_logs."""
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO security_logs (
            session_id,
            question,
            attack_type,
            reason
        )
        VALUES (?, ?, ?, ?)
        """,
        (session_id, question, attack_type, reason),
    )

    event_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return int(event_id)


# =========================================================
# US-013 : RATE LIMITING
# =========================================================

RATE_LIMIT_MAX_QUESTIONS = 10
RATE_LIMIT_WINDOW_SECONDS = 60


def get_recent_question_count(connection: sqlite3.Connection, session_id: str) -> int:
    """Compte les questions valides de la session sur les 60 dernieres secondes."""
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS request_count
        FROM question_logs
        WHERE session_id = ?
          AND timestamp >= datetime('now', ?)
        """,
        (session_id, f"-{RATE_LIMIT_WINDOW_SECONDS} seconds"),
    )
    row = cursor.fetchone()
    return int(row["request_count"] or 0)


def log_rate_limit_event(
    connection: sqlite3.Connection,
    session_id: str,
    question: str,
    request_count: int,
) -> int:
    """Enregistre un depassement de la limite de requetes."""
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO rate_limit_logs (
            session_id,
            question,
            request_count,
            limit_value
        )
        VALUES (?, ?, ?, ?)
        """,
        (session_id, question, request_count, RATE_LIMIT_MAX_QUESTIONS),
    )
    return int(cursor.lastrowid)


# =========================================================
# API TEST / DATA
# =========================================================


@app.get("/")
def accueil():
    return {
        "message": "Chatbot Campus API OK",
        "datasets_loaded": len(knowledge_base),
        "faq_questions": len(faq_items),
    }


@app.get("/data-status")
def data_status():
    return {
        "knowledge_entries": len(knowledge_base),
        "faq_questions": len(faq_items),
        "pdf_chunks": len(pdf_chunks),
        "load_errors": load_errors,
        "data_directory": str(DATA_DIR),
    }


# =========================================================
# SESSIONS
# =========================================================


@app.post("/session")
def create_session():
    session_id = str(uuid4())

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO sessions (
            session_id,
            context_version,
            context_topic
        )
        VALUES (?, 1, NULL)
        """,
        (session_id,),
    )

    session_number = cursor.lastrowid

    connection.commit()
    connection.close()

    return {
        "session_id": session_id,
        "session_number": session_number,
        "context_version": 1,
    }


# =========================================================
# CHAT
# =========================================================


@app.post("/chat")
def chat(data: Question):
    question = data.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="La question ne peut pas être vide.",
        )

    # =====================================================
    # US-012 : DETECTION ET BLOCAGE D'INJECTION
    # =====================================================
    blocked, attack_type, reason = detect_injection(question)

    if blocked:
        security_log_id = log_security_event(
            data.session_id,
            question,
            attack_type or "unknown",
            reason or "rule_match",
        )

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Requête bloquée pour des raisons de sécurité.",
                "security_event_id": security_log_id,
                "attack_type": attack_type,
            },
        )

    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            context_version,
            context_topic
        FROM sessions
        WHERE session_id = ?
        """,
        (data.session_id,),
    )

    session = cursor.fetchone()

    if session is None:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Session inconnue",
        )

    # =====================================================
    # US-013 : RATE LIMITING
    # =====================================================
    recent_question_count = get_recent_question_count(
        connection,
        data.session_id,
    )

    if recent_question_count >= RATE_LIMIT_MAX_QUESTIONS:
        rate_limit_log_id = log_rate_limit_event(
            connection,
            data.session_id,
            question,
            recent_question_count + 1,
        )
        connection.commit()
        connection.close()

        raise HTTPException(
            status_code=429,
            detail={
                "message": (
                    "Trop de questions envoyées. "
                    "Veuillez patienter avant de réessayer."
                ),
                "rate_limit_log_id": rate_limit_log_id,
                "limit": RATE_LIMIT_MAX_QUESTIONS,
                "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
                "retry_after_seconds": RATE_LIMIT_WINDOW_SECONDS,
            },
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )

    # =====================================================
    # US-011 : ENREGISTREMENT DE LA QUESTION
    # =====================================================
    # La question est journalisée dès sa réception, avant
    # la génération de la réponse. Le timestamp est généré
    # par SQLite en UTC (CURRENT_TIMESTAMP).
    cursor.execute(
        """
        INSERT INTO question_logs (
            session_id,
            question
        )
        VALUES (?, ?)
        """,
        (data.session_id, question),
    )

    question_log_id = cursor.lastrowid

    cursor.execute(
        "SELECT timestamp FROM question_logs WHERE id = ?",
        (question_log_id,),
    )
    question_log = cursor.fetchone()
    question_timestamp = question_log["timestamp"] if question_log else None

    # On valide définitivement l'enregistrement de la question
    # indépendamment de la génération de la réponse.
    connection.commit()

    current_version = session["context_version"]
    current_topic = session["context_topic"]

    if current_topic is None:
        current_topic = detecter_sujet(question)

        cursor.execute(
            """
            UPDATE sessions
            SET context_topic = ?
            WHERE session_id = ?
            """,
            (current_topic, data.session_id),
        )

    answer, answer_type = generate_answer(
        question,
        current_topic,
    )

    cursor.execute(
        """
        INSERT INTO messages (
            session_id,
            question,
            answer,
            context_version
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            data.session_id,
            question,
            answer,
            current_version,
        ),
    )

    connection.commit()
    connection.close()

    return {
        "question": question,
        "answer": answer,
        "session_id": data.session_id,
        "context_version": current_version,
        "context_topic": current_topic,
        "source": answer_type,
        "question_log_id": question_log_id,
        "question_timestamp": question_timestamp,
    }


# =========================================================
# US-011 : JOURNAL DES QUESTIONS
# =========================================================


@app.get("/questions")
def get_question_logs(session_id: str | None = None, limit: int = 100):
    """
    Retourne les questions enregistrées avec leur timestamp.

    - Sans session_id : toutes les questions.
    - Avec session_id : uniquement celles de la session demandée.
    - limit : nombre maximum de lignes retournées.
    """
    limit = max(1, min(limit, 1000))

    connection = get_db()
    cursor = connection.cursor()

    if session_id:
        cursor.execute(
            """
            SELECT
                id,
                session_id,
                question,
                timestamp
            FROM question_logs
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
    else:
        cursor.execute(
            """
            SELECT
                id,
                session_id,
                question,
                timestamp
            FROM question_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

    questions = cursor.fetchall()
    connection.close()

    return {
        "count": len(questions),
        "questions": [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "question": row["question"],
                "timestamp": row["timestamp"],
            }
            for row in questions
        ],
    }


# =========================================================
# US-013 : JOURNAL DES DEPASSEMENTS DE RATE LIMIT
# =========================================================


@app.get("/rate-limit-logs")
def get_rate_limit_logs(session_id: str | None = None, limit: int = 100):
    """Retourne les tentatives bloquees pour depassement de rate limit."""
    limit = max(1, min(limit, 1000))

    connection = get_db()
    cursor = connection.cursor()

    if session_id:
        cursor.execute(
            """
            SELECT
                id,
                session_id,
                question,
                request_count,
                limit_value,
                timestamp
            FROM rate_limit_logs
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
    else:
        cursor.execute(
            """
            SELECT
                id,
                session_id,
                question,
                request_count,
                limit_value,
                timestamp
            FROM rate_limit_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

    rows = cursor.fetchall()
    connection.close()

    return {
        "count": len(rows),
        "rate_limit_events": [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "question": row["question"],
                "request_count": row["request_count"],
                "limit_value": row["limit_value"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ],
    }


# =========================================================
# US-012 : JOURNAL DE SECURITE
# =========================================================


@app.get("/security-logs")
def get_security_logs(session_id: str | None = None, limit: int = 100):
    """
    Retourne les tentatives d'injection bloquees.

    - Sans session_id : toutes les tentatives recentes.
    - Avec session_id : uniquement les tentatives de la session.
    - limit : 1 a 1000 lignes.
    """
    limit = max(1, min(limit, 1000))

    connection = get_db()
    cursor = connection.cursor()

    if session_id:
        cursor.execute(
            """
            SELECT
                id,
                session_id,
                question,
                attack_type,
                reason,
                timestamp
            FROM security_logs
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
    else:
        cursor.execute(
            """
            SELECT
                id,
                session_id,
                question,
                attack_type,
                reason,
                timestamp
            FROM security_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

    rows = cursor.fetchall()
    connection.close()

    return {
        "count": len(rows),
        "security_events": [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "question": row["question"],
                "attack_type": row["attack_type"],
                "reason": row["reason"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ],
    }


# =========================================================
# CONTEXTE
# =========================================================


@app.post("/context/reset/{session_id}")
def reset_context(session_id: str):
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            context_version
        FROM sessions
        WHERE session_id = ?
        """,
        (session_id,),
    )

    session = cursor.fetchone()

    if session is None:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Session inconnue",
        )

    new_version = session["context_version"] + 1

    cursor.execute(
        """
        UPDATE sessions
        SET
            context_version = ?,
            context_topic = NULL
        WHERE session_id = ?
        """,
        (new_version, session_id),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Contexte de conversation réinitialisé",
        "session_id": session_id,
        "context_version": new_version,
    }


# =========================================================
# HISTORIQUE D'UNE SESSION
# =========================================================


@app.get("/history/{session_id}")
def get_history(session_id: str):
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            created_at,
            context_version,
            context_topic
        FROM sessions
        WHERE session_id = ?
        """,
        (session_id,),
    )

    session = cursor.fetchone()

    if session is None:
        connection.close()
        return {
            "session_id": session_id,
            "session_number": None,
            "history": [],
        }

    cursor.execute(
        """
        SELECT
            question,
            answer,
            context_version,
            created_at
        FROM messages
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,),
    )

    messages = cursor.fetchall()
    connection.close()

    return {
        "session_id": session_id,
        "session_number": session["id"],
        "context_version": session["context_version"],
        "context_topic": session["context_topic"],
        "created_at": session["created_at"],
        "history": [
            {
                "question": message["question"],
                "answer": message["answer"],
                "context_version": message["context_version"],
                "created_at": message["created_at"],
            }
            for message in messages
        ],
    }


# =========================================================
# TOUTES LES SESSIONS
# =========================================================


@app.get("/sessions")
def get_sessions():
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            s.id,
            s.session_id,
            s.created_at,
            s.context_version,
            s.context_topic,
            COUNT(m.id) AS message_count
        FROM sessions s
        LEFT JOIN messages m
            ON s.session_id = m.session_id
        GROUP BY
            s.id,
            s.session_id,
            s.created_at,
            s.context_version,
            s.context_topic
        ORDER BY s.id DESC
        """
    )

    sessions = cursor.fetchall()
    connection.close()

    return {
        "sessions": [
            {
                "session_number": session["id"],
                "session_id": session["session_id"],
                "created_at": session["created_at"],
                "context_version": session["context_version"],
                "context_topic": session["context_topic"],
                "message_count": session["message_count"],
            }
            for session in sessions
        ]
    }


# =========================================================
# SUGGESTIONS US-005
# =========================================================


@app.get("/suggestions")
def get_suggestions():
    priority = {
        "très élevée": 3,
        "elevee": 2,
        "élevée": 2,
        "moyenne": 1,
        "faible": 0,
    }

    selected_ids = {
        str(x)
        for x in (
            load_json_file("faq_complete.json")
            .get("statistiques", {})
            .get("questions_les_plus_frequentes", [])
        )
    }

    candidates = sorted(
        faq_items,
        key=lambda item: (
            1 if str(item.get("id")) in selected_ids else 0,
            priority.get(str(item.get("frequency", "")).lower(), 0),
        ),
        reverse=True,
    )

    return {
        "suggestions": [
            {
                "id": item.get("id"),
                "question": item.get("question"),
                "answer": item.get("answer"),
                "category": item.get("category"),
                "frequency": item.get("frequency"),
            }
            for item in candidates[:5]
        ]
    }


# =========================================================
# SUPPRIMER UNE CONVERSATION
# =========================================================


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    session = cursor.fetchone()

    if session is None:
        connection.close()
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    cursor.execute(
        "DELETE FROM messages WHERE session_id = ?",
        (session_id,),
    )
    cursor.execute(
        "DELETE FROM sessions WHERE session_id = ?",
        (session_id,),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Conversation supprimée",
        "session_id": session_id,
    }


# =========================================================
# EFFACER TOUT L'HISTORIQUE
# =========================================================


@app.delete("/sessions")
def clear_all_sessions():
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM sessions")

    try:
        cursor.execute(
            "DELETE FROM sqlite_sequence WHERE name = 'sessions'"
        )
    except sqlite3.OperationalError:
        pass

    connection.commit()
    connection.close()

    return create_session()


# =========================================================
# LANCEMENT
# =========================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )
