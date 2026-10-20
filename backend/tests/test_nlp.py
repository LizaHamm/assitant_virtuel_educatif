from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.services.nlp_services import analyze_question


# ============================================================
# TESTS DE CLASSIFICATION
# ============================================================
#
# IMPORTANT :
# Ces phrases servent uniquement à l'évaluation.
# NE PAS les ajouter au dataset d'entraînement.
#
# 90 questions :
# - 15 Planning
# - 15 Procédures administratives
# - 15 Services campus
# - 15 Règlement / vie étudiante
# - 15 Orientation / formation
# - 15 Contacts
#
# Intentions :
# - info
# - aide
# - reclamation
# ============================================================


TEST_CASES = [

    # ========================================================
    # 1 — EMPLOIS DU TEMPS ET PLANNING
    # ========================================================

    (
        "À quelle heure débute mon premier cours lundi ?",
        "Emplois du temps et planning",
        "info",
    ),
    (
        "Est-ce qu'une séance est prévue mercredi après-midi ?",
        "Emplois du temps et planning",
        "info",
    ),
    (
        "Quand auront lieu les partiels de ce semestre ?",
        "Emplois du temps et planning",
        "info",
    ),
    (
        "Je voudrais connaître la date des rattrapages.",
        "Emplois du temps et planning",
        "info",
    ),
    (
        "À quelle date commence la prochaine période de cours ?",
        "Emplois du temps et planning",
        "info",
    ),

    (
        "Impossible pour moi de retrouver l'horaire de mon prochain cours.",
        "Emplois du temps et planning",
        "aide",
    ),
    (
        "Je suis perdu, je ne sais pas dans quelle salle aller cet après-midi.",
        "Emplois du temps et planning",
        "aide",
    ),
    (
        "Pouvez-vous m'aider à retrouver l'heure de mon examen ?",
        "Emplois du temps et planning",
        "aide",
    ),
    (
        "Je ne sais plus quand je dois passer ma soutenance.",
        "Emplois du temps et planning",
        "aide",
    ),
    (
        "Je n'arrive pas à comprendre mon calendrier de cours.",
        "Emplois du temps et planning",
        "aide",
    ),

    (
        "L'horaire de mon examen a encore changé sans explication.",
        "Emplois du temps et planning",
        "reclamation",
    ),
    (
        "La salle annoncée pour le cours était la mauvaise.",
        "Emplois du temps et planning",
        "reclamation",
    ),
    (
        "Je souhaite signaler une erreur dans les horaires affichés.",
        "Emplois du temps et planning",
        "reclamation",
    ),
    (
        "Les dates de soutenance communiquées ne sont pas correctes.",
        "Emplois du temps et planning",
        "reclamation",
    ),
    (
        "Mon calendrier comporte plusieurs incohérences et je veux les signaler.",
        "Emplois du temps et planning",
        "reclamation",
    ),


    # ========================================================
    # 2 — PROCÉDURES ADMINISTRATIVES
    # ========================================================

    (
        "Quels documents sont nécessaires pour constituer mon dossier d'inscription ?",
        "Procédures administratives",
        "info",
    ),
    (
        "Quelle est la démarche pour obtenir un relevé de notes ?",
        "Procédures administratives",
        "info",
    ),
    (
        "Comment fonctionne la réinscription pour l'année prochaine ?",
        "Procédures administratives",
        "info",
    ),
    (
        "Quel est le délai pour faire signer une convention de stage ?",
        "Procédures administratives",
        "info",
    ),
    (
        "Quelles démarches faut-il effectuer pour l'alternance ?",
        "Procédures administratives",
        "info",
    ),

    (
        "Je suis bloqué au moment de valider mon dossier d'inscription.",
        "Procédures administratives",
        "aide",
    ),
    (
        "Je n'arrive pas à récupérer mon relevé de notes.",
        "Procédures administratives",
        "aide",
    ),
    (
        "Pouvez-vous m'expliquer comment compléter ma convention ?",
        "Procédures administratives",
        "aide",
    ),
    (
        "Je ne comprends pas les étapes pour me réinscrire.",
        "Procédures administratives",
        "aide",
    ),
    (
        "J'ai besoin d'aide pour constituer mon dossier de stage.",
        "Procédures administratives",
        "aide",
    ),

    (
        "Mon dossier administratif est en attente depuis un mois malgré mes relances.",
        "Procédures administratives",
        "reclamation",
    ),
    (
        "Je veux contester le refus de ma demande administrative.",
        "Procédures administratives",
        "reclamation",
    ),
    (
        "Mon relevé de notes contient une erreur que je souhaite signaler.",
        "Procédures administratives",
        "reclamation",
    ),
    (
        "Ma convention n'a toujours pas été traitée alors que je l'ai envoyée à temps.",
        "Procédures administratives",
        "reclamation",
    ),
    (
        "On m'a demandé plusieurs fois les mêmes justificatifs et je souhaite faire une réclamation.",
        "Procédures administratives",
        "reclamation",
    ),


    # ========================================================
    # 3 — SERVICES CAMPUS
    # ========================================================

    (
        "À quelle heure ferme la médiathèque en semaine ?",
        "Services campus",
        "info",
    ),
    (
        "Y a-t-il un endroit pour déjeuner sur le campus ?",
        "Services campus",
        "info",
    ),
    (
        "Existe-t-il des activités sportives proposées aux étudiants ?",
        "Services campus",
        "info",
    ),
    (
        "Où peut-on rencontrer un psychologue étudiant ?",
        "Services campus",
        "info",
    ),
    (
        "Est-ce qu'il existe des associations étudiantes à l'école ?",
        "Services campus",
        "info",
    ),

    (
        "Je n'arrive plus à accéder au réseau internet de l'école.",
        "Services campus",
        "aide",
    ),
    (
        "J'ai perdu l'accès à mon espace numérique, pouvez-vous m'aider ?",
        "Services campus",
        "aide",
    ),
    (
        "Je cherche de l'aide pour utiliser les ordinateurs du campus.",
        "Services campus",
        "aide",
    ),
    (
        "Je voudrais parler à quelqu'un du service de santé mais je ne sais pas comment faire.",
        "Services campus",
        "aide",
    ),
    (
        "Je ne trouve pas les ressources en ligne de la bibliothèque.",
        "Services campus",
        "aide",
    ),

    (
        "La connexion internet du campus coupe constamment depuis plusieurs jours.",
        "Services campus",
        "reclamation",
    ),
    (
        "Je souhaite signaler un problème récurrent avec les ordinateurs de l'école.",
        "Services campus",
        "reclamation",
    ),
    (
        "La bibliothèque était fermée pendant les horaires annoncés.",
        "Services campus",
        "reclamation",
    ),
    (
        "Je veux signaler un problème concernant le restaurant du campus.",
        "Services campus",
        "reclamation",
    ),
    (
        "Le support technique ne répond à aucune de mes demandes.",
        "Services campus",
        "reclamation",
    ),


    # ========================================================
    # 4 — RÈGLEMENT ET VIE ÉTUDIANTE
    # ========================================================

    (
        "Que prévoit le règlement lorsqu'un étudiant arrive en retard ?",
        "Règlement et vie étudiante",
        "info",
    ),
    (
        "Quelles sont les conséquences d'une absence non justifiée ?",
        "Règlement et vie étudiante",
        "info",
    ),
    (
        "Quelles règles s'appliquent pendant les examens ?",
        "Règlement et vie étudiante",
        "info",
    ),
    (
        "Quels sont les droits d'un étudiant en cas de sanction ?",
        "Règlement et vie étudiante",
        "info",
    ),
    (
        "Que prévoit l'école en cas de plagiat ?",
        "Règlement et vie étudiante",
        "info",
    ),

    (
        "Je ne comprends pas comment justifier correctement une absence.",
        "Règlement et vie étudiante",
        "aide",
    ),
    (
        "Pouvez-vous m'expliquer ce que je dois faire après avoir reçu un avertissement ?",
        "Règlement et vie étudiante",
        "aide",
    ),
    (
        "Je ne comprends pas la différence entre absence justifiée et injustifiée.",
        "Règlement et vie étudiante",
        "aide",
    ),
    (
        "J'ai besoin d'aide pour comprendre mes droits en tant qu'étudiant.",
        "Règlement et vie étudiante",
        "aide",
    ),
    (
        "Je ne comprends pas les règles concernant l'utilisation du matériel de l'école.",
        "Règlement et vie étudiante",
        "aide",
    ),

    (
        "Je considère que l'avertissement que j'ai reçu n'est pas justifié.",
        "Règlement et vie étudiante",
        "reclamation",
    ),
    (
        "Je souhaite faire appel d'une décision disciplinaire.",
        "Règlement et vie étudiante",
        "reclamation",
    ),
    (
        "Je veux signaler des propos irrespectueux tenus sur le campus.",
        "Règlement et vie étudiante",
        "reclamation",
    ),
    (
        "Je souhaite signaler une situation de harcèlement.",
        "Règlement et vie étudiante",
        "reclamation",
    ),
    (
        "Je veux contester la décision prise à la suite de mes absences.",
        "Règlement et vie étudiante",
        "reclamation",
    ),


    # ========================================================
    # 5 — ORIENTATION ET FORMATION
    # ========================================================

    (
        "Quels débouchés professionnels offre une formation en intelligence artificielle ?",
        "Orientation et formation",
        "info",
    ),
    (
        "Quelles compétences apprend-on pendant le cursus Data Science ?",
        "Orientation et formation",
        "info",
    ),
    (
        "Quelles conditions faut-il remplir pour intégrer le CPDIA ?",
        "Orientation et formation",
        "info",
    ),
    (
        "Le Bachelor permet-il ensuite de poursuivre en master ?",
        "Orientation et formation",
        "info",
    ),
    (
        "Quels enseignements sont proposés en cybersécurité ?",
        "Orientation et formation",
        "info",
    ),

    (
        "Je voudrais travailler dans l'IA mais je ne sais pas quel cursus choisir.",
        "Orientation et formation",
        "aide",
    ),
    (
        "Pouvez-vous m'orienter vers une formation adaptée au développement informatique ?",
        "Orientation et formation",
        "aide",
    ),
    (
        "J'hésite entre la Data Science et l'intelligence artificielle.",
        "Orientation et formation",
        "aide",
    ),
    (
        "Je ne sais pas si le CPDIA correspond à mon projet professionnel.",
        "Orientation et formation",
        "aide",
    ),
    (
        "Aidez-moi à comprendre quelle formation correspond à mon niveau.",
        "Orientation et formation",
        "aide",
    ),

    (
        "Les matières enseignées ne correspondent pas à ce qui était annoncé pour mon cursus.",
        "Orientation et formation",
        "reclamation",
    ),
    (
        "Je souhaite signaler une incohérence dans le programme de ma formation.",
        "Orientation et formation",
        "reclamation",
    ),
    (
        "Le programme pédagogique présenté au début de l'année n'est pas respecté.",
        "Orientation et formation",
        "reclamation",
    ),
    (
        "Je veux faire une réclamation concernant le contenu de mon cursus.",
        "Orientation et formation",
        "reclamation",
    ),
    (
        "Plusieurs enseignements annoncés dans ma formation ne sont finalement pas proposés.",
        "Orientation et formation",
        "reclamation",
    ),


    # ========================================================
    # 6 — CONTACTS ET INFORMATION GÉNÉRALE
    # ========================================================

    (
        "À quelle adresse puis-je écrire au secrétariat ?",
        "Contacts et information générale",
        "info",
    ),
    (
        "Quel est le numéro pour joindre l'accueil de l'école ?",
        "Contacts et information générale",
        "info",
    ),
    (
        "À qui faut-il s'adresser pour parler à un responsable pédagogique ?",
        "Contacts et information générale",
        "info",
    ),
    (
        "Comment puis-je joindre le responsable du CPDIA ?",
        "Contacts et information générale",
        "info",
    ),
    (
        "Qui est mon interlocuteur pour une question concernant mon cursus ?",
        "Contacts et information générale",
        "info",
    ),

    (
        "Je ne sais pas quel service contacter pour mon problème.",
        "Contacts et information générale",
        "aide",
    ),
    (
        "Aidez-moi à trouver la personne à qui envoyer mon message.",
        "Contacts et information générale",
        "aide",
    ),
    (
        "Je cherche à joindre quelqu'un de l'administration mais je ne sais pas qui.",
        "Contacts et information générale",
        "aide",
    ),
    (
        "Je ne sais pas à quelle adresse envoyer ma demande.",
        "Contacts et information générale",
        "aide",
    ),
    (
        "Pouvez-vous m'orienter vers le bon interlocuteur ?",
        "Contacts et information générale",
        "aide",
    ),

    (
        "Cela fait plusieurs jours que personne ne répond au téléphone de l'accueil.",
        "Contacts et information générale",
        "reclamation",
    ),
    (
        "L'adresse de contact indiquée sur les documents ne fonctionne pas.",
        "Contacts et information générale",
        "reclamation",
    ),
    (
        "Je souhaite signaler que les coordonnées communiquées sont incorrectes.",
        "Contacts et information générale",
        "reclamation",
    ),
    (
        "Personne ne répond à mes mails malgré plusieurs relances.",
        "Contacts et information générale",
        "reclamation",
    ),
    (
        "Le contact indiqué pour le service concerné n'est plus valide.",
        "Contacts et information générale",
        "reclamation",
    ),
]


# ============================================================
# TESTS D'ENTITÉS
# ============================================================

ENTITY_CASES = [

    (
        "Je suis en Master Intelligence Artificielle.",
        {
            "formation": ["Master IA"],
        },
    ),

    (
        "Je suis en CPDIA.",
        {
            "formation": ["CPDIA"],
        },
    ),

    (
        "Je cherche des informations sur la cybersécurité.",
        {
            "formation": ["Cybersécurité"],
        },
    ),

    (
        "Je voudrais une formation en développement informatique.",
        {
            "formation": ["Développement"],
        },
    ),

    (
        "Je cherche la médiathèque.",
        {
            "service": ["Bibliothèque"],
        },
    ),

    (
        "Où se trouve le restaurant U ?",
        {
            "service": ["Restaurant universitaire"],
        },
    ),

    (
        "Je voudrais contacter l'infirmerie.",
        {
            "service": ["Santé"],
        },
    ),

    (
        "Comment contacter le BDE ?",
        {
            "service": ["Associations étudiantes"],
        },
    ),

    (
        "Mon cours est dans la salle B204.",
        {
            "lieu": ["salle B204"],
        },
    ),

    (
        "Le rendez-vous est au bureau 205.",
        {
            "lieu": ["bureau 205"],
        },
    ),

    (
        "Mon examen aura lieu le 24 octobre 2026.",
        {
            "date": ["24 octobre 2026"],
        },
    ),

    (
        "J'ai un cours demain.",
        {
            "date": ["demain"],
        },
    ),

    (
        "Mon rendez-vous est prévu la semaine prochaine.",
        {
            "date": ["semaine prochaine"],
        },
    ),

    (
        "Je cherche la scolarité.",
        {
            "service": ["Scolarité"],
        },
    ),

    (
        "J'ai besoin du support informatique.",
        {
            "service": ["Informatique"],
        },
    ),
]


# ============================================================
# TESTS DE CLARIFICATION
# ============================================================

CLARIFICATION_CASES = [

    (
        "Et après ?",
        True,
    ),

    (
        "C'est où ?",
        True,
    ),

    (
        "Je dois faire quoi ?",
        True,
    ),

    (
        "Pour mon inscription ?",
        True,
    ),

    (
        "Mon planning ?",
        True,
    ),

    (
        "Bonjour",
        False,
    ),

    (
        "Merci beaucoup",
        False,
    ),

    (
        "Quels documents faut-il pour une convention de stage ?",
        False,
    ),

    (
        "Je suis en CPDIA, quel est mon emploi du temps ?",
        False,
    ),

    (
        "Je souhaite contester une sanction pour absence.",
        False,
    ),
]


# ============================================================
# OUTILS D'AFFICHAGE
# ============================================================

def separator():
    print("=" * 90)


def check_expected_entities(
    detected,
    expected,
):
    errors = []

    for entity_type, expected_values in expected.items():

        actual_values = detected.get(
            entity_type,
            [],
        )

        actual_normalized = [
            str(value).casefold()
            for value in actual_values
        ]

        for expected_value in expected_values:

            expected_normalized = (
                str(expected_value).casefold()
            )

            found = any(
                expected_normalized
                in actual_value
                or actual_value
                in expected_normalized
                for actual_value in actual_normalized
            )

            if not found:
                errors.append(
                    (
                        entity_type,
                        expected_value,
                        actual_values,
                    )
                )

    return errors


# ============================================================
# TEST CLASSIFICATION
# ============================================================

def test_classification():

    separator()
    print(
        "TEST NLP V2 — CLASSIFICATION "
        "(PHRASES DE TEST)"
    )
    separator()

    category_success = 0
    intent_success = 0

    low_category = 0
    low_intent = 0

    errors = []

    for index, (
        text,
        expected_category,
        expected_intent,
    ) in enumerate(TEST_CASES, 1):

        result = analyze_question(text)

        category_ok = (
            result["category"]
            == expected_category
        )

        intent_ok = (
            result["intent"]
            == expected_intent
        )

        if category_ok:
            category_success += 1

        if intent_ok:
            intent_success += 1

        if result.get(
            "category_low_confidence",
            False,
        ):
            low_category += 1

        if result.get(
            "intent_low_confidence",
            False,
        ):
            low_intent += 1

        if not category_ok or not intent_ok:
            errors.append(
                {
                    "index": index,
                    "text": text,
                    "expected_category": (
                        expected_category
                    ),
                    "actual_category": (
                        result["category"]
                    ),
                    "category_confidence": (
                        result[
                            "category_confidence"
                        ]
                    ),
                    "expected_intent": (
                        expected_intent
                    ),
                    "actual_intent": (
                        result["intent"]
                    ),
                    "intent_confidence": (
                        result[
                            "intent_confidence"
                        ]
                    ),
                }
            )

    total = len(TEST_CASES)

    print()
    print(
        f"Catégories : "
        f"{category_success}/{total} = "
        f"{category_success / total:.1%}"
    )

    print(
        f"Intentions : "
        f"{intent_success}/{total} = "
        f"{intent_success / total:.1%}"
    )

    print()
    print(
        "Confiance catégorie < 45% : "
        f"{low_category}/{total}"
    )

    print(
        "Confiance intention < 45% : "
        f"{low_intent}/{total}"
    )

    print()

    separator()
    print("ERREURS DE CLASSIFICATION")
    separator()

    if not errors:
        print(
            "\nAucune erreur sur ce jeu de test."
        )

    else:
        for error in errors:

            print()
            print(
                f"[{error['index']:02d}] "
                f"{error['text']}"
            )

            if (
                error["actual_category"]
                != error["expected_category"]
            ):
                print(
                    "  CATEGORIE :"
                )
                print(
                    "    attendu : "
                    f"{error['expected_category']}"
                )
                print(
                    "    obtenu  : "
                    f"{error['actual_category']} "
                    f"("
                    f"{error['category_confidence']:.2%}"
                    f")"
                )

            if (
                error["actual_intent"]
                != error["expected_intent"]
            ):
                print(
                    "  INTENTION :"
                )
                print(
                    "    attendu : "
                    f"{error['expected_intent']}"
                )
                print(
                    "    obtenu  : "
                    f"{error['actual_intent']} "
                    f"("
                    f"{error['intent_confidence']:.2%}"
                    f")"
                )

    return (
        category_success,
        intent_success,
        total,
    )


# ============================================================
# TEST ENTITÉS
# ============================================================

def test_entities():

    print()
    separator()
    print("TEST NLP V2 — EXTRACTION D'ENTITÉS")
    separator()

    success = 0

    for index, (
        text,
        expected,
    ) in enumerate(ENTITY_CASES, 1):

        result = analyze_question(text)

        entities = result["entities"]

        errors = check_expected_entities(
            entities,
            expected,
        )

        ok = not errors

        if ok:
            success += 1

        print()
        print(
            f"[{index:02d}] {text}"
        )

        if ok:
            print("  OK")

        else:
            print("  ERREUR")

            for (
                entity_type,
                expected_value,
                actual_values,
            ) in errors:

                print(
                    f"    {entity_type}"
                    f" attendu : "
                    f"{expected_value}"
                )

                print(
                    f"    obtenu : "
                    f"{actual_values}"
                )

        print(
            f"  Détecté : {entities}"
        )

    total = len(ENTITY_CASES)

    print()
    print(
        f"Entités : "
        f"{success}/{total} = "
        f"{success / total:.1%}"
    )

    return success, total


# ============================================================
# TEST CLARIFICATION
# ============================================================

def test_clarification():

    print()
    separator()
    print("TEST NLP V2 — CLARIFICATION")
    separator()

    success = 0

    for index, (
        text,
        expected,
    ) in enumerate(
        CLARIFICATION_CASES,
        1,
    ):

        result = analyze_question(text)

        actual = bool(
            result["clarification"]["required"]
        )

        ok = actual == expected

        if ok:
            success += 1

        print()
        print(
            f"[{index:02d}] {text!r}"
        )

        print(
            f"  attendu : {expected}"
        )

        print(
            f"  obtenu  : {actual}"
        )

        print(
            f"  résultat : "
            f"{'OK' if ok else 'ERREUR'}"
        )

        if actual:
            print(
                "  question : "
                f"{result['clarification']['question']}"
            )

            print(
                "  raison   : "
                f"{result['clarification'].get('reason')}"
            )

    total = len(CLARIFICATION_CASES)

    print()
    print(
        f"Clarification : "
        f"{success}/{total} = "
        f"{success / total:.1%}"
    )

    return success, total


# ============================================================
# MAIN
# ============================================================

def main():

    (
        category_success,
        intent_success,
        classification_total,
    ) = test_classification()

    (
        entity_success,
        entity_total,
    ) = test_entities()

    (
        clarification_success,
        clarification_total,
    ) = test_clarification()

    print()
    separator()
    print("BILAN FINAL NLP V2")
    separator()

    category_score = (
        category_success
        / classification_total
    )

    intent_score = (
        intent_success
        / classification_total
    )

    entity_score = (
        entity_success
        / entity_total
    )

    clarification_score = (
        clarification_success
        / clarification_total
    )

    print()
    print(
        f"Catégories     : "
        f"{category_score:.1%}"
    )

    print(
        f"Intentions     : "
        f"{intent_score:.1%}"
    )

    print(
        f"Entités        : "
        f"{entity_score:.1%}"
    )

    print(
        f"Clarification  : "
        f"{clarification_score:.1%}"
    )

    print()

    if (
        category_score >= 0.85
        and intent_score >= 0.85
        and entity_score >= 0.85
        and clarification_score >= 0.85
    ):
        print(
            "RESULTAT GLOBAL : OK"
        )
        print(
            "Les quatre blocs testés "
            "atteignent au moins 85%."
        )

    else:
        print(
            "RESULTAT GLOBAL : "
            "AMELIORATIONS NECESSAIRES"
        )

        if category_score < 0.85:
            print(
                "- Classification catégorie "
                "à améliorer."
            )

        if intent_score < 0.85:
            print(
                "- Classification intention "
                "à améliorer."
            )

        if entity_score < 0.85:
            print(
                "- Extraction d'entités "
                "à améliorer."
            )

        if clarification_score < 0.85:
            print(
                "- Clarification "
                "à améliorer."
            )


if __name__ == "__main__":
    main()