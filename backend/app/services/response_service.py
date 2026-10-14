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
)


# ============================================================
# US-006 — HORAIRES
# ============================================================

def is_hours_question(question):

    question = normalize_text(question)

    keywords = [
        "horaire",
        "horaires",
        "heure",
        "heures",
        "ouvre",
        "ouvert",
        "ouverture",
        "ferme",
        "fermeture",
        "quand est ouvert",
        "quand ouvre",
        "quand ferme",
    ]

    return any(
        keyword in question
        for keyword in keywords
    )


# ============================================================
# US-007 — CONTACT SCOLARITÉ
# ============================================================

def is_scolarite_contact_question(question):

    question = normalize_text(question)

    contact_keywords = [
        "contact",
        "contacter",
        "joindre",
        "email",
        "mail",
        "telephone",
        "tel",
        "numero",
        "coordonnees",
        "adresse",
    ]

    scolarite_keywords = [
        "scolarite",
        "scolaire",
    ]

    has_contact_keyword = any(
        keyword in question
        for keyword in contact_keywords
    )

    has_scolarite_keyword = any(
        keyword in question
        for keyword in scolarite_keywords
    )

    return (
        has_contact_keyword
        and has_scolarite_keyword
    )


# ============================================================
# US-008 — RÈGLES DU CAMPUS
# ============================================================

def is_campus_rules_question(question):

    question = normalize_text(question)

    keywords = [
        "regles du campus",
        "reglement interieur",
        "reglement",
        "regles de vie",
        "vie du campus",
        "regles generales",
        "regles esic",
        "regles de l esic",
        "droits et devoirs",
        "discipline",
        "sanctions",
        "securite",
        "securite du campus",
        "acces aux locaux",
    ]

    return any(
        keyword in question
        for keyword in keywords
    )


# ============================================================
# FRAUDE / PLAGIAT
# ============================================================

def is_fraud_question(question):

    question = normalize_text(question)

    keywords = [
        "fraude",
        "frauder",
        "plagiat",
        "plagier",
        "triche",
        "tricher",
        "triche examen",
        "fraude examen",
        "sanction fraude",
    ]

    return any(
        keyword in question
        for keyword in keywords
    )


# ============================================================
# DISCIPLINE / SANCTIONS
# ============================================================

def is_discipline_question(question):

    question = normalize_text(question)

    keywords = [
        "discipline",
        "sanction",
        "sanctions",
        "conseil de discipline",
        "exclusion",
        "exclu",
        "avertissement",
        "blame",
        "blâme",
    ]

    return any(
        keyword in question
        for keyword in keywords
    )


# ============================================================
# DROITS / DEVOIRS
# ============================================================

def is_rights_duties_question(question):

    question = normalize_text(question)

    keywords = [
        "droits et devoirs",
        "droits des etudiants",
        "devoirs des etudiants",
        "obligations des etudiants",
        "obligations etudiants",
    ]

    return any(
        keyword in question
        for keyword in keywords
    )


# ============================================================
# SÉCURITÉ
# ============================================================

def is_security_question(question):

    question = normalize_text(question)

    keywords = [
        "securite",
        "securite du campus",
        "regles de securite",
        "incendie",
        "evacuation",
        "issue de secours",
        "issues de secours",
        "urgence",
        "accident",
    ]

    return any(
        keyword in question
        for keyword in keywords
    )


# ============================================================
# ACCÈS AUX LOCAUX
# ============================================================

def is_access_question(question):

    question = normalize_text(question)

    keywords = [
        "acces aux locaux",
        "acces au campus",
        "acceder au campus",
        "horaires du campus",
        "fermeture du campus",
        "ouverture du campus",
    ]

    return any(
        keyword in question
        for keyword in keywords
    )


# ============================================================
# CALENDRIER / US-009
# ============================================================

def is_calendar_question(question):

    question = normalize_text(question)

    keywords = [
        "date importante",
        "dates importantes",
        "calendrier",
        "examen",
        "examens",
        "vacances",
        "rattrapage",
        "rattrapages",
        "semestre",
        "soutenance",
        "soutenances",
        "stage",
        "stages",
    ]

    return any(
        keyword in question
        for keyword in keywords
    )


# ============================================================
# DÉTECTION DU SERVICE
# ============================================================

def detect_service(question):

    question = normalize_text(question)

    services = {

        "bibliotheque": [
            "bibliotheque",
            "mediatheque",
        ],

        "restaurant": [
            "restaurant",
            "restaurant universitaire",
            "restaurant u",
        ],

        "cafeteria": [
            "cafeteria",
        ],

        "infirmerie": [
            "infirmerie",
            "infirmiere",
            "sante",
        ],

        "helpdesk": [
            "helpdesk",
            "informatique",
            "service informatique",
            "support informatique",
        ],

        "scolarite": [
            "scolarite",
        ],

        "accueil": [
            "accueil",
        ],

        "musculation": [
            "musculation",
            "salle de musculation",
            "salle musculation",
        ],
    }

    for service, keywords in services.items():

        for keyword in keywords:

            if keyword in question:
                return service

    return None


# ============================================================
# FORMATAGE DES HORAIRES
# ============================================================

def format_hours(
    service_name,
    result
):

    if not result:
        return None

    horaires = result.get(
        "horaires",
        {}
    )

    labels = {

        "lundi_vendredi":
            "Lundi à vendredi",

        "samedi":
            "Samedi",

        "dimanche":
            "Dimanche",

        "periode_examens":
            "Période d'examens",

        "chat_en_ligne":
            "Chat en ligne",

        "lundi":
            "Lundi",

        "mardi":
            "Mardi",

        "mercredi":
            "Mercredi",

        "jeudi":
            "Jeudi",

        "vendredi":
            "Vendredi",
    }

    service_labels = {

        "bibliotheque":
            "la bibliothèque",

        "restaurant_universitaire":
            "le restaurant universitaire",

        "cafeteria":
            "la cafétéria",

        "infirmerie":
            "l'infirmerie",

        "helpdesk_informatique":
            "le helpdesk informatique",

        "scolarite":
            "la scolarité",

        "accueil_general":
            "l'accueil",

        "salle_musculation":
            "la salle de musculation",
    }

    display_name = service_labels.get(
        result.get("service"),
        service_name
    )

    response = (
        f"Les horaires de {display_name} sont :\n"
    )

    for key, value in horaires.items():

        label = labels.get(
            key,
            key.replace(
                "_",
                " "
            ).capitalize()
        )

        response += (
            f"- {label} : {value}\n"
        )

    return response.strip()


# ============================================================
# FORMATAGE CONTACT SCOLARITÉ
# ============================================================

def format_scolarite_contact(contact):

    if not contact:
        return None

    responsable = contact.get(
        "responsable",
        {}
    )

    prenom = responsable.get(
        "prenom",
        ""
    )

    nom = responsable.get(
        "nom",
        ""
    )

    email = responsable.get(
        "email",
        "Non renseigné"
    )

    telephone = responsable.get(
        "telephone",
        "Non renseigné"
    )

    bureau = contact.get(
        "bureau",
        "Non renseigné"
    )

    batiment = contact.get(
        "batiment",
        "Non renseigné"
    )

    horaires = contact.get(
        "horaires",
        "Non renseignés"
    )

    response = (
        "Voici les coordonnées du service Scolarité :\n\n"
        f"- Responsable : {prenom} {nom}\n"
        f"- Email : {email}\n"
        f"- Téléphone : {telephone}\n"
        f"- Bureau : {bureau}\n"
        f"- Bâtiment : {batiment}\n"
        f"- Horaires : {horaires}"
    )

    equipe = contact.get(
        "equipe",
        []
    )

    if equipe:

        response += (
            "\n\nÉquipe de la scolarité :"
        )

        for personne in equipe:

            p_prenom = personne.get(
                "prenom",
                ""
            )

            p_nom = personne.get(
                "nom",
                ""
            )

            poste = personne.get(
                "poste",
                ""
            )

            email_personne = personne.get(
                "email",
                ""
            )

            telephone_personne = personne.get(
                "telephone",
                ""
            )

            response += (
                f"\n- {p_prenom} {p_nom}"
                f" — {poste}"
                f" — {email_personne}"
                f" — {telephone_personne}"
            )

    return response

# ============================================================
# US-010 — FORMATIONS PROPOSÉES AUX VISITEURS
# ============================================================

def is_formations_question(question):

    question = normalize_text(question)

    keywords = [
        "formation",
        "formations",
        "programme",
        "programmes",
        "filiere",
        "filieres",
        "cursus",
        "etudes",
        "etudier",
        "proposees",
        "proposes",
    ]

    visitor_keywords = [
        "visiteur",
        "visiteurs",
        "futur etudiant",
        "futurs etudiants",
        "prospect",
        "lyceen",
        "lyceenne",
        "quelles formations",
        "quels programmes",
        "quels cursus",
    ]

    has_formation_keyword = any(
        keyword in question
        for keyword in keywords
    )

    has_visitor_keyword = any(
        keyword in question
        for keyword in visitor_keywords
    )

    return (
        has_formation_keyword
        and has_visitor_keyword
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

        if nom:
            response += f"- {nom}"

            if code:
                response += f" ({code})"

            if niveau:
                response += f" — {niveau}"

            if groupes:
                response += f" — Groupes : {', '.join(groupes)}"

            response += "\n"

    return response.strip()

# ============================================================
# RÉPONSE PRINCIPALE
# ============================================================

def generate_response(question):

    question_normalized = normalize_text(
        question
    )

    # --------------------------------------------------------
    # CONTACT SCOLARITÉ
    # --------------------------------------------------------

    if is_scolarite_contact_question(
        question_normalized
    ):

        contact = get_scolarite_contact()

        response = format_scolarite_contact(
            contact
        )

        if response:
            return response

        return (
            "Je n'ai pas trouvé les coordonnées "
            "de la scolarité dans la base de connaissances."
        )

    # --------------------------------------------------------
    # FRAUDE / PLAGIAT
    # --------------------------------------------------------

    if is_fraud_question(
        question_normalized
    ):

        fraud = get_fraud_information()

        if fraud:

            return (
                "Voici les informations du règlement "
                "intérieur concernant la fraude et le plagiat :\n\n"
                + fraud
            )

        return (
            "Je n'ai pas trouvé les informations "
            "sur la fraude et le plagiat dans le règlement intérieur."
        )

    # --------------------------------------------------------
    # DISCIPLINE / SANCTIONS
    # --------------------------------------------------------

    if is_discipline_question(
        question_normalized
    ):

        discipline = get_discipline_information()

        if discipline:

            return (
                "Voici les informations du règlement "
                "intérieur concernant la discipline et les sanctions :\n\n"
                + discipline
            )

        return (
            "Je n'ai pas trouvé les informations "
            "sur la discipline et les sanctions dans le règlement intérieur."
        )

    # --------------------------------------------------------
    # DROITS ET DEVOIRS
    # --------------------------------------------------------

    if is_rights_duties_question(
        question_normalized
    ):

        rights_duties = get_rights_and_duties()

        if rights_duties:

            return (
                "Voici les droits et devoirs des étudiants "
                "selon le règlement intérieur :\n\n"
                + rights_duties
            )

        return (
            "Je n'ai pas trouvé les droits et devoirs "
            "des étudiants dans le règlement intérieur."
        )

    # --------------------------------------------------------
    # SÉCURITÉ
    # --------------------------------------------------------

    if is_security_question(
        question_normalized
    ):

        security = get_security_rules()

        if security:

            return (
                "Voici les règles de sécurité et de santé "
                "du règlement intérieur :\n\n"
                + security
            )

        return (
            "Je n'ai pas trouvé les règles de sécurité "
            "dans le règlement intérieur."
        )

    # --------------------------------------------------------
    # ACCÈS AUX LOCAUX
    # --------------------------------------------------------

    if is_access_question(
        question_normalized
    ):

        access = get_access_rules()

        if access:

            return (
                "Voici les règles concernant l'accès aux locaux :\n\n"
                + access
            )

        return (
            "Je n'ai pas trouvé les règles d'accès aux locaux "
            "dans le règlement intérieur."
        )

    # --------------------------------------------------------
    # RÈGLES GÉNÉRALES DU CAMPUS
    # --------------------------------------------------------

    if is_campus_rules_question(
        question_normalized
    ):

        campus_rules = get_campus_rules()

        if campus_rules:

            return (
                "Voici les principales règles du campus "
                "selon le règlement intérieur de l'ESIC :\n\n"
                + campus_rules
            )

        return (
            "Je n'ai pas pu extraire les règles du campus "
            "depuis le règlement intérieur."
        )

    # --------------------------------------------------------
    # HORAIRES
    # --------------------------------------------------------

    if is_hours_question(
        question_normalized
    ):

        service = detect_service(
            question_normalized
        )

        if service:

            result = get_service_hours(
                service
            )

            response = format_hours(
                service,
                result
            )

            if response:
                return response

        all_hours = get_service_hours()

        if all_hours:

            response = (
                "Voici les principaux horaires "
                "des services du campus :\n\n"
            )

            labels = {

                "accueil_general":
                    "Accueil",

                "scolarite":
                    "Scolarité",

                "bibliotheque":
                    "Bibliothèque",

                "restaurant_universitaire":
                    "Restaurant universitaire",

                "cafeteria":
                    "Cafétéria",

                "salle_musculation":
                    "Salle de musculation",

                "infirmerie":
                    "Infirmerie",

                "helpdesk_informatique":
                    "Helpdesk informatique",
            }

            for service_key, horaires in all_hours.items():

                label = labels.get(
                    service_key,
                    service_key.replace(
                        "_",
                        " "
                    ).capitalize()
                )

                response += (
                    f"{label} :\n"
                )

                for key, value in horaires.items():

                    response += (
                        f"  - "
                        f"{key.replace('_', ' ').capitalize()}"
                        f" : {value}\n"
                    )

                response += "\n"

            return response.strip()

        return (
            "Je n'ai pas trouvé les horaires demandés "
            "dans la base de connaissances."
        )



    # ============================================================
    # US-010 — FORMATIONS PROPOSÉES
    # ============================================================

    def is_formations_question(question):
        question = normalize_text(question)

        formation_keywords = [
            "formation",
            "formations",
            "programme",
            "programmes",
            "filiere",
            "filieres",
            "cursus",
            "etudes",
            "parcours",
            "diplome",
            "diplomes",
        ]

        visitor_keywords = [
            "visiteur",
            "visiteurs",
            "visite",
            "visiter",
            "prospect",
            "prospects",
            "futur etudiant",
            "future etudiante",
            "futur étudiant",
            "future étudiante",
            "lyceen",
            "lyceenne",
            "lycéen",
            "lycéenne",
            "candidat",
            "candidats",
        ]

        has_formation_keyword = any(
            keyword in question
            for keyword in formation_keywords
        )

        has_visitor_keyword = any(
            keyword in question
            for keyword in visitor_keywords
        )

        return (
            has_formation_keyword
            or has_visitor_keyword
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
            effectif = formation.get("effectif_total")

            response += f"- {code} — {nom}\n"
            response += f"  Niveau : {niveau}\n"

            if groupes:
                response += (
                    f"  Groupes : {', '.join(groupes)}\n"
                )

            if effectif is not None:
                response += (
                    f"  Effectif total : {effectif}\n"
                )

            response += "\n"

        return response.strip()
    
    # FORMATIONS / US-010
    if is_formations_question(question_normalized):
        formations = get_formations()
        response = format_formations(formations)

        if response:
            return response

        return (
            "Je n'ai pas trouvé la liste des formations "
            "dans la base de connaissances."
        )
         
    # --------------------------------------------------------
    # CALENDRIER / US-009
    # --------------------------------------------------------

    if is_calendar_question(
        question_normalized
    ):

        calendar = format_calendar()

        if calendar:
            return calendar

        return (
            "Je n'ai pas trouvé les dates demandées "
            "dans le calendrier."
        )

    # --------------------------------------------------------
    # SALUTATIONS
    # --------------------------------------------------------

    if (
        "bonjour" in question_normalized
        or "salut" in question_normalized
        or "hello" in question_normalized
    ):

        return (
            "Bonjour ! Je suis l'assistant virtuel "
            "éducatif ESIC. Comment puis-je vous aider ?"
        )

    # --------------------------------------------------------
    # REMERCIEMENTS
    # --------------------------------------------------------

    if "merci" in question_normalized:

        return "Avec plaisir !"

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return (
        "Je n'ai pas encore trouvé de réponse précise "
        "à cette question dans ma base de connaissances."
    )