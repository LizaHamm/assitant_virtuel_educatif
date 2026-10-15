import json
import os
import re
import sqlite3
import unicodedata
import uuid
from collections import Counter
from datetime import datetime, timedelta
from difflib import SequenceMatcher
 
from flask import Flask, request, jsonify
from flask_cors import CORS
from pypdf import PdfReader
 
app = Flask(__name__)
CORS(app)
 
CONVERSATIONS = {}
 
WELCOME_TEXT = "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. Comment puis-je vous aider ?"
 
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
 
 
def normaliser(texte: str) -> str:
    """Enlève les accents et met en minuscules, pour comparer plus facilement."""
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return texte.lower()
 
 
def now_iso():
    return datetime.now().isoformat()
 
 
def now_time():
    return datetime.now().strftime("%H:%M")
 
 
# =====================================================================
# Chargement du dataset annuaire (US-006, US-007)
# =====================================================================
with open(os.path.join(DATA_DIR, "annuaire_contacts.json"), encoding="utf-8") as f:
    ANNUAIRE = json.load(f)
 
HORAIRES_BRUTS = ANNUAIRE["horaires_services"]
SERVICES_ADMIN = ANNUAIRE["services_administratifs"]
 
with open(os.path.join(DATA_DIR, "emploi_du_temps.json"), encoding="utf-8") as f:
    EMPLOI_DU_TEMPS = json.load(f)
 
DATES_IMPORTANTES = EMPLOI_DU_TEMPS["dates_importantes"]
SEMESTRES = EMPLOI_DU_TEMPS["metadata"]["semestres"]
ANNEE_ACADEMIQUE = EMPLOI_DU_TEMPS["metadata"]["annee_academique"]
 
 
# =====================================================================
# US-006 : horaires d'ouverture des services
# =====================================================================
LIBELLES_SERVICES = {
    "accueil_general": ("de l'accueil", ["accueil"]),
    "scolarite": ("du service scolarité", ["scolarite"]),
    "bibliotheque": ("de la bibliothèque", ["bibliotheque", "mediatheque"]),
    "restaurant_universitaire": ("du restaurant universitaire", ["resto", "restaurant", "cantine", "manger"]),
    "cafeteria": ("de la cafétéria", ["cafeteria", "snack"]),
    "salle_musculation": ("de la salle de musculation", ["musculation", "salle de sport", "gym", "muscu"]),
    "infirmerie": ("de l'infirmerie", ["infirmerie", "infirmiere", "medecin"]),
    "helpdesk_informatique": ("du helpdesk informatique", ["helpdesk", "informatique", "support it", "wifi"]),
}
 
JOURS_LISIBLES = {
    "lundi_vendredi": "du lundi au vendredi",
    "samedi": "le samedi",
    "dimanche": "le dimanche",
    "lundi": "le lundi",
    "mardi": "le mardi",
    "mercredi": "le mercredi",
    "jeudi": "le jeudi",
    "vendredi": "le vendredi",
    "chat_en_ligne": "le chat en ligne",
    "periode_examens": "pendant les examens",
}
 
 
def formater_horaires(details: dict) -> str:
    morceaux = [f"{JOURS_LISIBLES.get(cle, cle)} : {valeur}" for cle, valeur in details.items()]
    return ", ".join(morceaux) + "."
 
 
def construire_reponses_horaires() -> dict:
    reponses = {}
    for cle_dataset, (libelle, mots_cles) in LIBELLES_SERVICES.items():
        details = HORAIRES_BRUTS.get(cle_dataset)
        if not details:
            continue
        texte = f"Les horaires {libelle} sont : {formater_horaires(details)}"
        reponses[cle_dataset] = {"mots_cles": mots_cles, "texte": texte}
    return reponses
 
 
HORAIRES = construire_reponses_horaires()
 
 
def repondre_horaires(q: str):
    for service in HORAIRES.values():
        if any(mot in q for mot in service["mots_cles"]):
            return service["texte"]
    return None
 
 
# =====================================================================
# US-009 : dates importantes du calendrier académique
# =====================================================================
def formater_date(date_iso: str) -> str:
    """Transforme 2025-01-06 en 06/01/2025, plus lisible pour l'étudiant."""
    annee, mois, jour = date_iso.split("-")
    return f"{jour}/{mois}/{annee}"
 
 
def ligne_evenement(evenement: dict) -> str:
    return f"- {formater_date(evenement['date'])} : {evenement['evenement']}"
 
 
def repondre_calendrier(q: str):
    # --- Le calendrier complet, avec toutes les dates ---
    if any(mot in q for mot in [
        "dates importantes", "calendrier academique", "calendrier scolaire",
        "toutes les dates", "echeances importantes", "calendrier de l'annee",
    ]):
        lignes = [f"Voici les dates importantes de l'année {ANNEE_ACADEMIQUE} :"]
        lignes += [ligne_evenement(e) for e in DATES_IMPORTANTES]
        return "\n".join(lignes)
 
    # --- Rattrapages : avant "examen" générique, car plus précis ---
    if "rattrapage" in q:
        evenements = [e for e in DATES_IMPORTANTES if "rattrapage" in normaliser(e["evenement"])]
        if evenements:
            lignes = ["Dates des rattrapages :"] + [ligne_evenement(e) for e in evenements]
            return "\n".join(lignes)
 
    # --- Vacances ---
    if "vacance" in q:
        evenements = [e for e in DATES_IMPORTANTES if e["type"] == "Vacances"]
        if evenements:
            lignes = ["Dates des vacances :"] + [ligne_evenement(e) for e in evenements]
            return "\n".join(lignes)
 
    # --- Examens (hors rattrapages, déjà traités au-dessus) ---
    if any(mot in q for mot in ["examen", "examens"]) and any(
        mot in q for mot in ["quand", "date", "dates", "calendrier", "periode", "debut", "fin", "commence"]
    ):
        evenements = [e for e in DATES_IMPORTANTES if e["type"] == "Examens"]
        if evenements:
            lignes = ["Dates des examens et rattrapages :"] + [ligne_evenement(e) for e in evenements]
            return "\n".join(lignes)
 
    # --- Période de stages ---
    if any(mot in q for mot in ["stage", "stages"]) and any(
        mot in q for mot in ["quand", "date", "dates", "periode", "debut", "fin"]
    ):
        evenements = [e for e in DATES_IMPORTANTES if e["type"] == "Stage"]
        if evenements:
            lignes = ["Dates de la période de stages :"] + [ligne_evenement(e) for e in evenements]
            return "\n".join(lignes)
 
    # --- Rentrée ---
    if "rentree" in q:
        evenements = [e for e in DATES_IMPORTANTES if e["type"] == "Rentrée"]
        if evenements:
            lignes = ["Dates de rentrée :"] + [ligne_evenement(e) for e in evenements]
            return "\n".join(lignes)
 
    # --- Semestres : dates de début/fin, avec vacances/examens/stages inclus ---
    if "semestre" in q:
        semestre_demande = None
        if "s1" in q or "semestre 1" in q:
            semestre_demande = "S1"
        elif "s2" in q or "semestre 2" in q:
            semestre_demande = "S2"
 
        semestres = [s for s in SEMESTRES if semestre_demande is None or s["semestre"] == semestre_demande]
        if semestres:
            lignes = [f"Calendrier {ANNEE_ACADEMIQUE} :"]
            for s in semestres:
                lignes.append(f"- {s['semestre']} : du {formater_date(s['debut'])} au {formater_date(s['fin'])}")
                for vac in s.get("vacances", []):
                    lignes.append(f"  - Vacances de {vac['nom']} : du {formater_date(vac['debut'])} au {formater_date(vac['fin'])}")
                if "examens" in s:
                    lignes.append(f"  - Examens : du {formater_date(s['examens']['debut'])} au {formater_date(s['examens']['fin'])}")
                if "stages" in s:
                    lignes.append(f"  - Stages : du {formater_date(s['stages']['debut'])} au {formater_date(s['stages']['fin'])}")
            return "\n".join(lignes)
 
    return None
 
 
# =====================================================================
# US-007 : contacts des services administratifs (scolarité, etc.)
# =====================================================================
MOTS_CONTACT = ["contact", "contacter", "email", "mail", "telephone", "tel", "numero", "joindre", "coordonnees"]
 
ALIAS_SERVICES_ADMIN = {
    "Scolarité": ["scolarite"],
    "Comptabilité et Finances": ["comptabilite", "finance", "financier"],
    "Admissions": ["admission"],
    "Communication": ["communication"],
    "Helpdesk IT": ["helpdesk", "support it", "informatique"],
}
 
 
def formater_contact(service: dict) -> str:
    resp = service.get("responsable", {})
    lignes = [
        f"{service['service']} :",
        f"Responsable : {resp.get('prenom', '')} {resp.get('nom', '')}",
        f"Email : {resp.get('email', 'non renseigné')}",
        f"Téléphone : {resp.get('telephone', 'non renseigné')}",
        f"Bureau : {service.get('bureau', 'non renseigné')} ({service.get('batiment', '')})",
        f"Horaires : {service.get('horaires', 'non renseignés')}",
    ]
    return "\n".join(lignes)
 
 
def repondre_contact(q: str):
    if not any(mot in q for mot in MOTS_CONTACT):
        return None
 
    for service in SERVICES_ADMIN:
        alias_liste = ALIAS_SERVICES_ADMIN.get(service["service"], [])
        if any(alias in q for alias in alias_liste):
            return formater_contact(service)
 
    return None
 
 
# =====================================================================
# US-008 : règlement intérieur, chargé et cherché directement dans le PDF
# =====================================================================
MOTS_VIDES = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "a", "au", "aux",
    "est", "sont", "en", "sur", "dans", "pour", "que", "qui", "quoi", "comment",
    "quel", "quelle", "quels", "quelles", "mon", "ma", "mes", "ton", "ta", "tes",
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "ce", "ces", "se",
    # mots trop génériques dans CE document : ils apparaissent dans presque
    # chaque paragraphe du règlement, donc ils ne doivent pas compter dans
    # le calcul de pertinence (sinon n'importe quel paragraphe "gagne" juste
    # parce qu'il contient le mot "règlement").
    "reglement", "regles", "regle", "interieur", "esic",
}
 
 
def decouper_en_mots(texte: str) -> set:
    texte = normaliser(texte)
    mots = re.findall(r"[a-z0-9]+", texte)
    return {m for m in mots if len(m) > 2 and m not in MOTS_VIDES}
 
 
def extraire_lignes_utiles_pdf(chemin_pdf: str) -> list:
    """Lit le PDF ligne par ligne et enlève le bruit (filigrane, sommaire, numéros de page)."""
    try:
        lecteur = PdfReader(chemin_pdf)
    except FileNotFoundError:
        print(f"[ATTENTION] PDF introuvable : {chemin_pdf}")
        return []
 
    lignes_utiles = []
    for page in lecteur.pages:
        texte_page = page.extract_text() or ""
        for ligne in texte_page.split("\n"):
            ligne = ligne.strip()
            if not ligne:
                continue
            # filigrane répété sur chaque page (parfois coupé sur 2 lignes,
            # donc on filtre aussi la ligne "Joel BANKA" isolée)
            if "projet étudiant" in ligne.lower() or "banka" in ligne.lower():
                continue
            # lignes de sommaire ("Discipline ................ 36")
            if re.search(r"\.{4,}", ligne):
                continue
            # lignes qui ne sont qu'un numéro de page
            if re.fullmatch(r"\d+", ligne):
                continue
            lignes_utiles.append(ligne)
    return lignes_utiles
 
 
TITRE_NUMEROTE = re.compile(r"^\d+(\.\d+)*\.?\s+\S")
 
 
def decouper_en_phrases(lignes: list) -> list:
    """Recolle les lignes du PDF en vraies phrases complètes (une phrase peut
    s'étaler sur plusieurs lignes dans le PDF), et garde les puces et les
    titres numérotés ("1.1 Objet du règlement") à part, pour qu'un titre ne
    se retrouve jamais collé au paragraphe qui le suit."""
    phrases = []
    buffer = ""
 
    for ligne in lignes:
        est_puce = bool(re.match(r"^[•\-\*]\s+", ligne))
        est_titre = bool(TITRE_NUMEROTE.match(ligne))
        texte_ligne = re.sub(r"^[•\-\*]\s+", "", ligne).strip()
 
        if est_puce or est_titre:
            # une puce ou un titre termine ce qui était en attente,
            # puis devient sa propre entrée
            if buffer.strip():
                phrases.append(buffer.strip())
                buffer = ""
            if len(texte_ligne) > 2:
                phrases.append(texte_ligne)
            continue
 
        # on recolle la ligne au morceau de phrase en cours de construction
        buffer = f"{buffer} {texte_ligne}".strip() if buffer else texte_ligne
 
        # on ne découpe que quand on a atteint une vraie fin de phrase
        # (ou si le morceau devient trop long, par sécurité)
        if re.search(r"[.!?]$", buffer) or len(buffer) > 400:
            for p in re.split(r"(?<=[.!?])\s+", buffer):
                p = p.strip()
                if len(p) > 3:
                    phrases.append(p)
            buffer = ""
 
    if buffer.strip():
        phrases.append(buffer.strip())
 
    return phrases
 
 
LIGNES_REGLEMENT = extraire_lignes_utiles_pdf(os.path.join(DATA_DIR, "reglement.pdf"))
REGLEMENT_PHRASES = decouper_en_phrases(LIGNES_REGLEMENT)
 
MOTS_REGLEMENT = [
    "reglement", "regle", "regles", "discipline", "sanction", "vie du campus",
    "vie etudiante", "comportement", "droit", "devoir", "fraude", "plagiat",
    "assiduite", "absence", "absences", "retard",
]
 
 
def score_similarite(question: str, texte: str) -> float:
    mots_question = decouper_en_mots(question)
    mots_texte = decouper_en_mots(texte)
    if not mots_question or not mots_texte:
        return 0.0
    return len(mots_question & mots_texte) / len(mots_question)
 
 
def repondre_reglement(question_originale: str, q_normalisee: str):
    if not any(mot in q_normalisee for mot in MOTS_REGLEMENT):
        return None
 
    if not REGLEMENT_PHRASES:
        return ("Le règlement intérieur n'a pas pu être chargé pour le moment. "
                "Il est disponible en PDF sur l'ENT.")
 
    # On note chaque phrase du règlement selon sa pertinence par rapport à la question
    # (on exclut les titres numérotés tout seuls, ex. "4.2 Absences" : ils servent
    # juste de repères internes, pas à être affichés comme réponse)
    phrases_notees = [
        (score_similarite(question_originale, phrase), index, phrase)
        for index, phrase in enumerate(REGLEMENT_PHRASES)
        if not TITRE_NUMEROTE.match(phrase)
    ]
    phrases_pertinentes = [p for p in phrases_notees if p[0] >= 0.3]
 
    if not phrases_pertinentes:
        return ("Le règlement intérieur complet est disponible en PDF sur l'ENT. "
                "Essaie de préciser ta question (ex : absences, fraude, sanctions, tenue, sécurité).")
 
    # On garde les meilleures phrases/puces, remises dans leur ordre d'origine
    # pour que la réponse finale reste cohérente à lire.
    # (seulement 2 : au-delà, on risque de mélanger des sections différentes
    # du règlement qui partagent juste quelques mots avec la question)
    meilleur_score = max(p[0] for p in phrases_pertinentes)
    candidats_proches = [p for p in phrases_pertinentes if p[0] >= meilleur_score - 0.15]
    meilleures = sorted(candidats_proches, key=lambda p: p[0], reverse=True)[:2]
    meilleures.sort(key=lambda p: p[1])
 
    indices_retenus = {index for _, index, _ in meilleures}
    morceaux = []
 
    for _, index, phrase in meilleures:
        morceaux.append(phrase if phrase.endswith((".", "!", "?", ":")) else phrase + ".")
 
        # si la phrase annonce une liste ("... pour :"), on va chercher
        # directement les éléments de cette liste juste après dans le PDF,
        # même s'ils n'ont pas été choisis par le score tout seuls.
        if phrase.rstrip().endswith(":"):
            suivant = index + 1
            ajouts = 0
            while suivant < len(REGLEMENT_PHRASES) and ajouts < 6:
                phrase_suivante = REGLEMENT_PHRASES[suivant]
                if TITRE_NUMEROTE.match(phrase_suivante):
                    break  # on est arrivé à la section suivante, on arrête
                if suivant not in indices_retenus:
                    texte = phrase_suivante if phrase_suivante.endswith((".", "!", "?", ":")) else phrase_suivante + "."
                    morceaux.append(texte)
                    ajouts += 1
                suivant += 1
 
    return " ".join(morceaux)
 
 
# =====================================================================
# US-010 : formations proposées par l'ESIC
# =====================================================================
FORMATIONS = EMPLOI_DU_TEMPS["formations"]
 
# Spécialisations issues du Guide de l'étudiant ESIC (section "Spécialisations proposées")
SPECIALISATIONS_BACHELOR = [
    "Développement Informatique",
    "Cybersécurité et Réseaux",
    "Data Science et IA",
    "Digital Marketing",
    "Management de Projets IT",
]
 
SPECIALISATIONS_MASTER = [
    "Ingénierie Logicielle et DevOps",
    "Cybersécurité et Sécurité des SI",
    "Intelligence Artificielle et Big Data",
    "Transformation Digitale",
    "Management de l'Innovation",
    "Chief Product Officer",
]
 
MOTS_CLES_FORMATION = {
    "B1": ["bachelor 1", "b1"],
    "B2": ["bachelor 2", "b2"],
    "B3-DEV": ["developpement informatique", "dev informatique", "b3-dev", "b3 dev"],
    "B3-CYBER": ["cybersecurite", "cyber", "b3-cyber", "b3 cyber"],
    "B3-DATA": ["data science", "data", "b3-data", "b3 data"],
    "M1-IA": ["m1-ia", "m1 ia", "master 1 ia", "master 1 intelligence artificielle"],
    "M1-CYBER": ["m1-cyber", "m1 cyber", "master 1 cyber"],
    "M2-IA": ["m2-ia", "m2 ia", "master 2 ia", "master 2 intelligence artificielle"],
}
 
 
def ligne_formation(formation: dict) -> str:
    groupes = ", ".join(formation.get("groupes", []))
    return (
        f"- {formation['nom']} ({formation['code']}, {formation['niveau']}) : "
        f"{formation.get('effectif_total', '?')} étudiants, groupes {groupes}"
    )
 
 
def repondre_formations(q: str):
    # --- Spécialisations (Bachelor 3 ou Master) ---
    if "specialisation" in q:
        if "master" in q:
            lignes = ["Spécialisations proposées en Master (Bac+5) :"]
            lignes += [f"- {s}" for s in SPECIALISATIONS_MASTER]
            return "\n".join(lignes)
        if "bachelor" in q or "b3" in q or "licence" in q:
            lignes = ["Spécialisations proposées en Bachelor 3 (Bac+3) :"]
            lignes += [f"- {s}" for s in SPECIALISATIONS_BACHELOR]
            return "\n".join(lignes)
        lignes = ["Spécialisations Bachelor (Bac+3) :"]
        lignes += [f"- {s}" for s in SPECIALISATIONS_BACHELOR]
        lignes.append("")
        lignes.append("Spécialisations Master (Bac+5) :")
        lignes += [f"- {s}" for s in SPECIALISATIONS_MASTER]
        return "\n".join(lignes)
 
    # --- Formation précise nommée dans la question ---
    for code, mots_cles in MOTS_CLES_FORMATION.items():
        if any(mot in q for mot in mots_cles):
            formation = next((f for f in FORMATIONS if f["code"] == code), None)
            if formation:
                return ligne_formation(formation)
 
    # --- Filtrage par niveau : Bachelor (Bac+3) ou Master (Bac+5) ---
    if "bachelor" in q and "master" not in q:
        formations = [f for f in FORMATIONS if f["code"].startswith("B")]
        lignes = ["Les formations Bachelor proposées sont :"] + [ligne_formation(f) for f in formations]
        return "\n".join(lignes)
 
    if "master" in q and "bachelor" not in q:
        formations = [f for f in FORMATIONS if f["code"].startswith("M")]
        lignes = ["Les formations Master proposées sont :"] + [ligne_formation(f) for f in formations]
        return "\n".join(lignes)
 
    # --- Question générale : toutes les formations ---
    if any(mot in q for mot in [
        "formation", "formations", "filiere", "filieres", "cursus",
        "parcours", "programme", "diplome", "diplomes",
    ]):
        lignes = ["Les formations proposées par l'ESIC sont :", "", "Bachelor (Bac+3) :"]
        lignes += [ligne_formation(f) for f in FORMATIONS if f["code"].startswith("B")]
        lignes.append("")
        lignes.append("Master (Bac+5) :")
        lignes += [ligne_formation(f) for f in FORMATIONS if f["code"].startswith("M")]
        return "\n".join(lignes)
 
    return None
 
 
# --- Autres règles (salutations, examens, procédures...) ---
REGLES_DIVERSES = [
    (["examen", "examens", "soutenance"],
     "Le calendrier des examens et des soutenances est disponible sur l'ENT, rubrique Planning."),
 
    (["emploi du temps", "planning"],
     "Ton emploi du temps est consultable sur l'ENT, dans la rubrique Planning, filtrable par formation et groupe. "
     "Tu peux aussi me demander les horaires d'un service précis (ex : bibliothèque, scolarité, resto U)."),
 
    (["stage", "alternance", "convention"],
     "Pour une demande de stage, d'alternance ou de convention, le formulaire est disponible "
     "sur l'ENT, rubrique Démarches administratives."),
 
    (["certificat", "releve", "notes"],
     "Les certificats de scolarité et relevés de notes se demandent directement sur l'ENT, "
     "rubrique Documents administratifs."),
 
    (["bourse", "aide financiere"],
     "Les informations sur les bourses et aides sociales sont disponibles auprès du service social "
     "ou sur le CROUS."),
 
    (["merci"],
     "Avec plaisir ! N'hésite pas si tu as d'autres questions."),
 
    (["bonjour", "salut", "hello", "coucou"],
     WELCOME_TEXT),
]
 
FALLBACK = "Je n'ai pas encore de réponse précise pour « {question} », mais je note votre question."
 
 
def trouver_reponse(question: str):
    """Renvoie (réponse, catégorie). La catégorie correspond à la fonction qui a
    répondu : ça sert de classification "maison" pour le dashboard (US-020),
    sans dépendre du NLP de l'Epic 4."""
    q = normaliser(question)
 
    reponse = repondre_contact(q)
    if reponse:
        return reponse, "contact"
 
    reponse = repondre_horaires(q)
    if reponse:
        return reponse, "horaires"
 
    reponse = repondre_calendrier(q)
    if reponse:
        return reponse, "calendrier"
 
    reponse = repondre_reglement(question, q)
    if reponse:
        return reponse, "reglement"
 
    reponse = repondre_formations(q)
    if reponse:
        return reponse, "formations"
 
    for mots_cles, texte in REGLES_DIVERSES:
        if any(mot in q for mot in mots_cles):
            return texte, "general"
 
    return FALLBACK.format(question=question), "sans_reponse"
 
 
# =====================================================================
# US-011 : enregistrement de chaque question avec timestamp (SQLite)
# =====================================================================
DB_PATH = os.path.join(os.path.dirname(__file__), "chatbot.db")
 
 
def initialiser_bdd() -> None:
    connexion = sqlite3.connect(DB_PATH)
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS questions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            reponse TEXT,
            horodatage TEXT NOT NULL
        )
    """)
 
    # Migration douce : si la base existe déjà depuis l'US-011 (sans colonne
    # "categorie"), on l'ajoute sans perdre les données déjà enregistrées.
    colonnes = [c[1] for c in connexion.execute("PRAGMA table_info(questions_log)").fetchall()]
    if "categorie" not in colonnes:
        connexion.execute("ALTER TABLE questions_log ADD COLUMN categorie TEXT")
 
    connexion.commit()
    connexion.close()
 
 
initialiser_bdd()
 
 
def enregistrer_question(session_id: str, question: str, reponse: str, categorie: str) -> None:
    """Enregistre la question posée avec son horodatage exact et sa catégorie.
    Une erreur ici ne doit jamais empêcher le chatbot de répondre (sous-tâche 9)."""
    try:
        connexion = sqlite3.connect(DB_PATH)
        connexion.execute(
            "INSERT INTO questions_log (session_id, question, reponse, horodatage, categorie) VALUES (?, ?, ?, ?, ?)",
            (session_id, question, reponse, now_iso(), categorie),
        )
        connexion.commit()
        connexion.close()
    except Exception as erreur:
        print(f"[ATTENTION] Échec de l'enregistrement de la question en base : {erreur}")
 
 
# =====================================================================
# US-012 : filtrage des tentatives d'injection
# =====================================================================
MOTIFS_INJECTION = [
    # --- Manipulation des instructions du chatbot ---
    (re.compile(r"ignor\w*\s+(tes|vos|les)?\s*instructions", re.IGNORECASE), "manipulation des instructions"),
    (re.compile(r"oublie\w*\s+(tes|vos)\s+instructions", re.IGNORECASE), "manipulation des instructions"),
    (re.compile(r"\bsystem\s*prompt\b", re.IGNORECASE), "manipulation des instructions"),
    (re.compile(r"\btu\s+es\s+maintenant\b", re.IGNORECASE), "manipulation des instructions"),
    (re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE), "manipulation des instructions"),
    (re.compile(r"\bjailbreak\b", re.IGNORECASE), "manipulation des instructions"),
    (re.compile(r"\bdan\s+mode\b", re.IGNORECASE), "manipulation des instructions"),
 
    # --- Injections SQL ---
    (re.compile(r"\bunion\s+select\b", re.IGNORECASE), "injection SQL"),
    (re.compile(r"\bdrop\s+table\b", re.IGNORECASE), "injection SQL"),
    (re.compile(r"\binsert\s+into\b", re.IGNORECASE), "injection SQL"),
    (re.compile(r"\bdelete\s+from\b", re.IGNORECASE), "injection SQL"),
    (re.compile(r"'\s*or\s*'?1'?\s*=\s*'?1", re.IGNORECASE), "injection SQL"),
    (re.compile(r"--\s"), "injection SQL"),
    (re.compile(r"/\*.*\*/"), "injection SQL"),
 
    # --- Exécution de commandes système ---
    (re.compile(r"\brm\s+-rf\b", re.IGNORECASE), "commande système"),
    (re.compile(r"\bos\.system\b", re.IGNORECASE), "commande système"),
    (re.compile(r"\bsubprocess\b", re.IGNORECASE), "commande système"),
    (re.compile(r"\bexec\s*\(", re.IGNORECASE), "commande système"),
    (re.compile(r"\beval\s*\(", re.IGNORECASE), "commande système"),
    (re.compile(r"\bsudo\s", re.IGNORECASE), "commande système"),
    (re.compile(r"/bin/(ba)?sh", re.IGNORECASE), "commande système"),
    (re.compile(r"\bpowershell\b", re.IGNORECASE), "commande système"),
]
 
 
def detecter_injection(question: str):
    """Renvoie le type de motif détecté (texte), ou None si la question est normale."""
    for motif, type_motif in MOTIFS_INJECTION:
        if motif.search(question):
            return type_motif
    return None
 
 
LOG_SECURITE_PATH = os.path.join(os.path.dirname(__file__), "logs_securite.txt")
 
 
def enregistrer_log_securite(session_id: str, question: str, raison: str) -> None:
    """Garde une trace des tentatives bloquées (injection ou dépassement de débit)."""
    try:
        with open(LOG_SECURITE_PATH, "a", encoding="utf-8") as f:
            f.write(f"{now_iso()} | session={session_id} | raison={raison} | question={question}\n")
    except Exception as erreur:
        print(f"[ATTENTION] Échec de l'écriture du log de sécurité : {erreur}")
 
 
# =====================================================================
# US-013 : limite de débit (10 questions / minute / conversation)
# =====================================================================
LIMITE_QUESTIONS = 10
FENETRE_SECONDES = 60
 
HISTORIQUE_REQUETES = {}  # { session_id: [timestamp, timestamp, ...] }
 
 
def verifier_limite(session_id: str) -> bool:
    """Renvoie False si la session a dépassé la limite de débit."""
    maintenant = datetime.now().timestamp()
    horodatages = HISTORIQUE_REQUETES.get(session_id, [])
 
    # on ne garde que les requêtes des 60 dernières secondes
    horodatages = [h for h in horodatages if maintenant - h < FENETRE_SECONDES]
 
    if len(horodatages) >= LIMITE_QUESTIONS:
        HISTORIQUE_REQUETES[session_id] = horodatages
        return False
 
    horodatages.append(maintenant)
    HISTORIQUE_REQUETES[session_id] = horodatages
    return True
 
 
def conversation_summary(conv):
    return {
        "id": conv["id"],
        "title": conv["title"],
        "pinned": conv["pinned"],
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
    }
 
 
@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    convs = sorted(CONVERSATIONS.values(), key=lambda c: c["updated_at"], reverse=True)
    convs = sorted(convs, key=lambda c: not c["pinned"])
    return jsonify({"conversations": [conversation_summary(c) for c in convs]})
 
 
@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    conv_id = str(uuid.uuid4())
    conv = {
        "id": conv_id,
        "title": "Nouvelle conversation",
        "pinned": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "messages": [],
    }
    CONVERSATIONS[conv_id] = conv
    return jsonify(conversation_summary(conv)), 201
 
 
@app.route("/api/conversations/<conversation_id>", methods=["PATCH"])
def update_conversation(conversation_id):
    conv = CONVERSATIONS.get(conversation_id)
    if conv is None:
        return jsonify({"error": "Conversation introuvable."}), 404
 
    data = request.get_json(silent=True) or {}
 
    if "title" in data:
        title = str(data["title"]).strip()
        if not title:
            return jsonify({"error": "Le titre est vide."}), 400
        conv["title"] = title[:60]
 
    if "pinned" in data:
        conv["pinned"] = bool(data["pinned"])
 
    return jsonify(conversation_summary(conv))
 
 
@app.route("/api/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    if CONVERSATIONS.pop(conversation_id, None) is None:
        return jsonify({"error": "Conversation introuvable."}), 404
    return jsonify({"deleted": conversation_id})
 
 
@app.route("/api/history/<conversation_id>", methods=["GET"])
def get_history(conversation_id):
    conv = CONVERSATIONS.get(conversation_id)
    messages = conv["messages"] if conv else []
    return jsonify({"conversation_id": conversation_id, "messages": messages})
 
 
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = data.get("message", "").strip()
    conversation_id = data.get("conversation_id", "").strip()
 
    if not question:
        return jsonify({"error": "Le message est vide."}), 400
 
    conv = CONVERSATIONS.get(conversation_id)
    if conv is None:
        return jsonify({"error": "Conversation introuvable."}), 404
 
    # US-013 : limite de débit (10 questions / minute / conversation)
    if not verifier_limite(conversation_id):
        enregistrer_log_securite(conversation_id, question, "limite de débit dépassée")
        return jsonify({
            "error": "Tu as posé trop de questions d'un coup. Merci de patienter quelques secondes avant de continuer."
        }), 429
 
    # US-012 : filtrage des tentatives d'injection
    motif_detecte = detecter_injection(question)
    if motif_detecte:
        enregistrer_log_securite(conversation_id, question, f"injection détectée ({motif_detecte})")
        return jsonify({
            "answer": "Je ne peux pas traiter cette question : elle contient des éléments non autorisés."
        })
 
    answer, categorie = trouver_reponse(question)
 
    conv["messages"].append({"id": str(uuid.uuid4()), "sender": "user", "text": question, "time": now_time()})
    conv["messages"].append({"id": str(uuid.uuid4()), "sender": "bot", "text": answer, "time": now_time()})
    conv["updated_at"] = now_iso()
 
    if conv["title"] == "Nouvelle conversation":
        conv["title"] = (question[:30] + "…") if len(question) > 30 else question
 
    # US-011 : enregistrement de la question avec timestamp + catégorie (US-020)
    enregistrer_question(conversation_id, question, answer, categorie)
 
    return jsonify({"answer": answer})
 
 
# =====================================================================
# Epic 5 : Dashboard Analytics (US-019 à US-022)
# =====================================================================
def lire_questions_log():
    connexion = sqlite3.connect(DB_PATH)
    connexion.row_factory = sqlite3.Row
    lignes = connexion.execute(
        "SELECT session_id, question, categorie, horodatage FROM questions_log"
    ).fetchall()
    connexion.close()
    return lignes
 
 
@app.route("/api/dashboard/top-questions", methods=["GET"])
def dashboard_top_questions():
    """US-019 : top des questions les plus posées (10 par défaut)."""
    limite = int(request.args.get("limite", 10))
    lignes = lire_questions_log()
 
    compteur = Counter(normaliser(l["question"]) for l in lignes)
 
    # on garde la formulation originale la plus "présentable" pour chaque question normalisée
    formulations = {}
    for l in lignes:
        cle = normaliser(l["question"])
        formulations.setdefault(cle, l["question"])
 
    top = compteur.most_common(limite)
    resultat = [{"question": formulations[cle], "nombre": nombre} for cle, nombre in top]
    return jsonify({"top_questions": resultat})
 
 
@app.route("/api/dashboard/categories", methods=["GET"])
def dashboard_categories():
    """US-020 : répartition des questions par catégorie."""
    lignes = lire_questions_log()
    compteur = Counter(l["categorie"] or "sans_categorie" for l in lignes)
    resultat = [{"categorie": cat, "nombre": nombre} for cat, nombre in compteur.most_common()]
    return jsonify({"categories": resultat})
 
 
@app.route("/api/dashboard/evolution", methods=["GET"])
def dashboard_evolution():
    """US-021 : évolution du volume de questions dans le temps (30 derniers jours par défaut)."""
    jours = int(request.args.get("jours", 30))
    lignes = lire_questions_log()
    compteur = Counter(l["horodatage"][:10] for l in lignes)  # "AAAA-MM-JJ"
 
    aujourdhui = datetime.now().date()
    resultat = []
    for i in range(jours - 1, -1, -1):
        jour = (aujourdhui - timedelta(days=i)).isoformat()
        resultat.append({"date": jour, "nombre": compteur.get(jour, 0)})
 
    return jsonify({"evolution": resultat})
 
 
@app.route("/api/dashboard/tendances", methods=["GET"])
def dashboard_tendances():
    """US-022 : sujets émergents, en comparant les 7 derniers jours à la semaine précédente."""
    lignes = lire_questions_log()
    aujourdhui = datetime.now().date()
 
    debut_semaine_actuelle = aujourdhui - timedelta(days=7)
    debut_semaine_precedente = aujourdhui - timedelta(days=14)
 
    compteur_actuel = Counter()
    compteur_precedent = Counter()
 
    for l in lignes:
        date_question = datetime.fromisoformat(l["horodatage"]).date()
        categorie = l["categorie"] or "sans_categorie"
        if date_question > debut_semaine_actuelle:
            compteur_actuel[categorie] += 1
        elif date_question > debut_semaine_precedente:
            compteur_precedent[categorie] += 1
 
    resultat = []
    for categorie in set(compteur_actuel) | set(compteur_precedent):
        actuel = compteur_actuel.get(categorie, 0)
        precedent = compteur_precedent.get(categorie, 0)
        resultat.append({
            "categorie": categorie,
            "questions_7_derniers_jours": actuel,
            "questions_7_jours_precedents": precedent,
            "evolution": actuel - precedent,
        })
 
    resultat.sort(key=lambda r: r["evolution"], reverse=True)
    return jsonify({"tendances": resultat})
 
 
if __name__ == "__main__":
    app.run(debug=True, port=8000)
 