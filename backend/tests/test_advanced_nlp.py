from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.services.advanced_nlp_service import (
    analyze_advanced_nlp,
    detect_sentiment_urgency,
)


# ============================================================
# TEST EXTERNE DES 15 INTENTIONS
# Ces phrases ne doivent PAS être ajoutées au dataset.
# ============================================================

TESTS = [

    (
        "Quels créneaux de cours ai-je mardi ?",
        "emploi_du_temps",
    ),
    (
        "Mon cours de vendredi est prévu à quelle heure ?",
        "emploi_du_temps",
    ),
    (
        "Je cherche l'heure et la salle de ma prochaine séance.",
        "emploi_du_temps",
    ),

    (
        "Comment faire éditer un justificatif de scolarité ?",
        "procedure_admin",
    ),
    (
        "Je dois récupérer un document officiel auprès de l'école.",
        "procedure_admin",
    ),
    (
        "Quel délai faut-il prévoir pour une demande administrative ?",
        "procedure_admin",
    ),

    (
        "Le resto U sert jusqu'à quelle heure ?",
        "service_campus",
    ),
    (
        "Y a-t-il une permanence médicale sur le campus ?",
        "service_campus",
    ),
    (
        "Je voudrais utiliser les équipements sportifs de l'école.",
        "service_campus",
    ),

    (
        "Le règlement autorise combien d'absences ?",
        "reglement",
    ),
    (
        "Quelles mesures disciplinaires existent pour le plagiat ?",
        "reglement",
    ),
    (
        "Quelles obligations un étudiant doit-il respecter ?",
        "reglement",
    ),

    (
        "Quels cours composent le cursus cybersécurité ?",
        "formation",
    ),
    (
        "Quels prérequis faut-il pour entrer en Data Science ?",
        "formation",
    ),
    (
        "À quels métiers prépare le Master IA ?",
        "formation",
    ),

    (
        "Je cherche l'adresse mail des admissions.",
        "contact",
    ),
    (
        "Qui dois-je joindre à la scolarité ?",
        "contact",
    ),
    (
        "Pouvez-vous me donner les coordonnées du helpdesk ?",
        "contact",
    ),

    (
        "Mon identifiant ENT est refusé.",
        "aide_technique",
    ),
    (
        "Je n'ai plus accès à mon compte numérique étudiant.",
        "aide_technique",
    ),
    (
        "La connexion Wi-Fi ESIC ne fonctionne pas.",
        "aide_technique",
    ),

    (
        "Je souhaite signaler que mon dossier a été mal traité.",
        "reclamation",
    ),
    (
        "Je ne suis pas d'accord avec la décision reçue.",
        "reclamation",
    ),
    (
        "Je veux déposer une plainte concernant une information erronée.",
        "reclamation",
    ),

    (
        "Pouvez-vous présenter brièvement l'école ?",
        "information_generale",
    ),
    (
        "À quoi sert ce chatbot étudiant ?",
        "information_generale",
    ),
    (
        "Je voudrais savoir ce qu'on peut trouver sur le campus en général.",
        "information_generale",
    ),

    (
        "Bonjour, assistant !",
        "salutation",
    ),
    (
        "Merci pour ces renseignements.",
        "salutation",
    ),
    (
        "À bientôt !",
        "salutation",
    ),

    (
        "À quelle date est prévue ma soutenance ?",
        "examen",
    ),
    (
        "Je voudrais savoir quand se déroule l'épreuve finale.",
        "examen",
    ),
    (
        "Où consulter les dates de partiels ?",
        "examen",
    ),

    (
        "Je dois faire signer ma convention par l'école.",
        "stage_alternance",
    ),
    (
        "Comment déclarer mon contrat d'apprentissage à ESIC ?",
        "stage_alternance",
    ),
    (
        "Quelles formalités sont nécessaires avant de commencer en entreprise ?",
        "stage_alternance",
    ),

    (
        "Comment valider mon inscription pour cette année ?",
        "inscription",
    ),
    (
        "Il me manque une pièce pour mon dossier d'inscription.",
        "inscription",
    ),
    (
        "Quelle procédure suivre pour renouveler mon inscription ?",
        "inscription",
    ),

    (
        "Existe-t-il une aide pour les étudiants en difficulté financière ?",
        "aide_financiere",
    ),
    (
        "Comment financer mon logement étudiant ?",
        "aide_financiere",
    ),
    (
        "Où demander un soutien social ou une bourse ?",
        "aide_financiere",
    ),

    (
        "Je voudrais participer aux activités du BDE.",
        "vie_etudiante",
    ),
    (
        "Quels clubs puis-je rejoindre cette année ?",
        "vie_etudiante",
    ),
    (
        "Y a-t-il des événements associatifs prochainement ?",
        "vie_etudiante",
    ),
]


SENTIMENT_TESTS = [

    (
        "Pouvez-vous me donner les horaires de la bibliothèque ?",
        "neutre",
        False,
    ),

    (
        "Merci beaucoup, c'est parfait !",
        "satisfaction",
        False,
    ),

    (
        "C'est inadmissible, aucune réponse depuis plusieurs jours !",
        "frustration",
        False,
    ),

    (
        "C'est urgent, je risque de perdre mon stage demain !",
        "urgent",
        True,
    ),

    (
        "Je suis très mécontente, rien ne change depuis des jours.",
        "frustration",
        False,
    ),

    (
        "URGENT !!! Je suis bloquée et la date limite est demain.",
        "urgent",
        True,
    ),
]


def test_semantic_intents():

    correct = 0

    print(
        "\n===== 15 INTENTIONS ====="
    )

    for text, expected in TESTS:

        result = analyze_advanced_nlp(
            text
        )

        predicted = (
            result["semantic_intent"]
        )

        confidence = (
            result[
                "semantic_intent_confidence"
            ]
        )

        if predicted == expected:

            correct += 1

        else:

            print(
                "\nERREUR"
            )

            print(
                "Question :",
                text,
            )

            print(
                "Attendu :",
                expected,
            )

            print(
                "Obtenu :",
                predicted,
            )

            print(
                "Confiance :",
                confidence,
            )

    accuracy = (
        correct
        / len(TESTS)
    )

    print(
        "\nRésultat : "
        f"{correct}/{len(TESTS)} "
        f"= {accuracy:.1%}"
    )

    return accuracy


def test_sentiment():

    correct = 0

    print(
        "\n===== SENTIMENT / URGENCE ====="
    )

    for (
        text,
        expected_sentiment,
        expected_escalation,
    ) in SENTIMENT_TESTS:

        result = (
            detect_sentiment_urgency(
                text
            )
        )

        success = (
            result["sentiment"]
            == expected_sentiment

            and

            result[
                "human_escalation_recommended"
            ]
            == expected_escalation
        )

        if success:

            correct += 1

        else:

            print(
                "\nERREUR"
            )

            print(
                "Question :",
                text,
            )

            print(
                "Attendu :",
                expected_sentiment,
                expected_escalation,
            )

            print(
                "Obtenu :",
                result,
            )

    accuracy = (
        correct
        / len(SENTIMENT_TESTS)
    )

    print(
        "\nRésultat : "
        f"{correct}/"
        f"{len(SENTIMENT_TESTS)} "
        f"= {accuracy:.1%}"
    )

    return accuracy


if __name__ == "__main__":

    semantic_accuracy = (
        test_semantic_intents()
    )

    sentiment_accuracy = (
        test_sentiment()
    )

    print(
        "\n=============================="
    )

    print(
        "RÉSULTAT FINAL"
    )

    print(
        "=============================="
    )

    print(
        "15 intentions >= 85% :",
        semantic_accuracy >= 0.85,
    )

    print(
        "Sentiment >= 85% :",
        sentiment_accuracy >= 0.85,
    )