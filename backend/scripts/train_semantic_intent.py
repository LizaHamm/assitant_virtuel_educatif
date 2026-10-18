"""Entraînement du modèle ESIC à 15 intentions sémantiques.

Emplacement :
backend/scripts/train_semantic_intent.py

Sorties :
data/semantic_intent_training.csv
models/nlp/semantic_intent_model.joblib
models/nlp/semantic_intent_labels.json
"""

from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline


BASE_DIR = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    BASE_DIR
    / "data"
    / "semantic_intent_training.csv"
)

MODEL_DIR = BASE_DIR / "models" / "nlp"

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATASET_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# DATASET
# ============================================================

SEEDS = {

    "emploi_du_temps": [
        "À quelle heure commence mon cours lundi ?",
        "Quel est mon planning de la semaine ?",
        "Dans quelle salle ai-je cours demain ?",
        "Je veux consulter mon emploi du temps.",
        "Quand a lieu mon prochain cours ?",
        "Quels cours sont prévus mercredi ?",
        "Où se déroule mon cours cet après-midi ?",
        "Mon planning de cours a-t-il changé ?",
    ],

    "procedure_admin": [
        "Comment obtenir un certificat de scolarité ?",
        "Quels documents faut-il fournir pour cette démarche ?",
        "Comment demander un relevé de notes ?",
        "Quelle est la procédure pour modifier mon dossier ?",
        "Où déposer un document administratif ?",
        "Quel est le délai de traitement de ma demande ?",
        "Comment récupérer une attestation de réussite ?",
        "Je cherche les étapes d'une démarche administrative.",
    ],

    "service_campus": [
        "Quels sont les horaires de la bibliothèque ?",
        "À quelle heure ouvre le restaurant universitaire ?",
        "Comment accéder à la salle de sport ?",
        "Quels services de santé sont disponibles ?",
        "La cafétéria est-elle ouverte aujourd'hui ?",
        "Comment utiliser les ressources numériques du campus ?",
        "Quels services sont proposés aux étudiants ?",
        "Où se trouve l'infirmerie ?",
        "Comment prendre rendez-vous avec le psychologue du campus ?",
        "Le service de psychologie reçoit-il sur rendez-vous ?",
    ],

    "reglement": [
        "Quelles sont les règles concernant les absences ?",
        "Que dit le règlement sur les retards ?",
        "Quelles sanctions sont prévues en cas de fraude ?",
        "Quels sont mes droits et devoirs ?",
        "Quelle est la règle concernant le plagiat ?",
        "Quelles consignes de sécurité dois-je respecter ?",
        "Puis-je contester une sanction disciplinaire ?",
        "Que prévoit le règlement intérieur ?",
        "Quelles conséquences sont prévues en cas de triche ?",
        "Les retards répétés sont-ils autorisés par le règlement ?",
    ],

    "formation": [
        "Quelles formations sont proposées par ESIC ?",
        "Quel est le contenu de la formation Data Science ?",
        "Quels sont les prérequis du Master IA ?",
        "Quels métiers peut-on faire après cette formation ?",
        "Quels modules sont enseignés en cybersécurité ?",
        "Quelle poursuite d'études est possible après le Bachelor ?",
        "Je veux connaître le programme de CPDIA.",
        "Quelles compétences développe cette formation ?",
        "Quels enseignements vais-je suivre en CPDIA ?",
        "Qu'est-ce qu'on apprend dans ce cursus ?",
    ],

    "contact": [
        "Comment contacter la scolarité ?",
        "Quel est l'email du service informatique ?",
        "Quel est le numéro de téléphone de l'accueil ?",
        "Qui est le responsable de cette formation ?",
        "Comment joindre le service des admissions ?",
        "Je cherche les coordonnées de la bibliothèque.",
        "À qui dois-je écrire pour cette question ?",
        "Où trouver le contact d'un responsable pédagogique ?",
    ],

    "aide_technique": [
        "Je n'arrive pas à me connecter à l'ENT.",
        "Mon mot de passe étudiant ne fonctionne plus.",
        "Le Wi-Fi du campus ne marche pas sur mon ordinateur.",
        "Je n'arrive pas à accéder à la plateforme numérique.",
        "Comment réinitialiser mon mot de passe ?",
        "Mon compte étudiant est bloqué.",
        "Je rencontre un problème avec l'accès informatique.",
        "Le portail étudiant affiche une erreur de connexion.",
        "L'authentification au réseau du campus est refusée.",
        "Je n'arrive pas à m'authentifier sur le Wi-Fi étudiant.",
    ],

    "reclamation": [
        "Je veux signaler une erreur dans mon dossier.",
        "Je souhaite faire une réclamation.",
        "Les informations affichées sont incorrectes.",
        "Je conteste la réponse donnée par le service.",
        "Mon problème n'a toujours pas été résolu.",
        "Je veux signaler un dysfonctionnement.",
        "La procédure annoncée n'a pas été respectée.",
        "Je suis mécontent du traitement de ma demande.",
    ],

    "information_generale": [
        "Où se trouve le campus ESIC ?",
        "Quels sont les horaires généraux de l'école ?",
        "Comment fonctionne ESIC Assistant ?",
        "Quelles informations puis-je demander au chatbot ?",
        "Comment accéder au campus ?",
        "Quels sont les principaux services de l'établissement ?",
        "Je voudrais des informations générales sur ESIC.",
        "Que peut faire l'assistant virtuel ?",
    ],

    "salutation": [
        "Bonjour",
        "Bonsoir",
        "Salut",
        "Coucou",
        "Hello",
        "Bonjour ESIC Assistant",
        "Salut, comment ça va ?",
        "Bonsoir, j'espère que vous allez bien",
        "Merci",
        "Merci beaucoup",
        "Au revoir",
        "Bonne journée",
        "Bonne soirée",
        "À bientôt",
        "Hello assistant",
        "Bonjour à vous",
    ],

    "examen": [
        "Quand auront lieu les examens ?",
        "Quelle est la date de mon partiel ?",
        "Dans quelle salle se déroule mon examen ?",
        "Quand sont les rattrapages ?",
        "Je cherche le calendrier des soutenances.",
        "À quelle heure commence mon épreuve ?",
        "Quand seront publiées les dates d'examen ?",
        "Je veux connaître le planning des partiels.",
    ],

    "stage_alternance": [
        "Comment obtenir une convention de stage ?",
        "Quelles démarches faut-il faire pour une alternance ?",
        "Qui doit signer ma convention de stage ?",
        "Comment faire valider mon entreprise d'accueil ?",
        "Quels documents faut-il pour démarrer un stage ?",
        "Je cherche les étapes pour mon contrat d'alternance.",
        "Comment déclarer mon stage à l'école ?",
        "Quelle procédure suivre pour une mission en entreprise ?",
    ],

    "inscription": [
        "Comment faire mon inscription pédagogique ?",
        "Quels documents sont nécessaires pour m'inscrire ?",
        "Comment me réinscrire l'année prochaine ?",
        "Mon dossier d'inscription est-il complet ?",
        "Quelle est la date limite d'inscription ?",
        "Comment modifier mon inscription ?",
        "Où déposer mon dossier de réinscription ?",
        "Je veux connaître les étapes pour finaliser mon inscription.",
    ],

    "aide_financiere": [
        "Comment demander une bourse ?",
        "Quelles aides financières existent pour les étudiants ?",
        "Puis-je obtenir une aide au logement ?",
        "Comment constituer un dossier de bourse ?",
        "À qui demander une aide sociale ?",
        "Quelles aides sont disponibles en cas de difficulté financière ?",
        "Comment connaître les conditions d'une bourse ?",
        "Je cherche une aide pour financer mes études.",
    ],

    "vie_etudiante": [
        "Quelles associations étudiantes existent ?",
        "Comment rejoindre le BDE ?",
        "Quelles activités sportives sont proposées ?",
        "Quels événements étudiants sont prévus ?",
        "Comment participer à la vie associative ?",
        "Y a-t-il des clubs étudiants sur le campus ?",
        "Quelles activités sont organisées pour les étudiants ?",
        "Comment proposer un événement étudiant ?",
        "Je voudrais adhérer à une association étudiante.",
        "Comment devenir membre d'un club du campus ?",
    ],
}


PREFIXES = [
    "",
    "Bonjour, ",
    "S'il vous plaît, ",
    "J'aimerais savoir : ",
    "Pouvez-vous me renseigner : ",
]


SUFFIXES = [
    "",
    " Merci.",
    " Pouvez-vous m'aider ?",
    " J'ai besoin de cette information.",
    " C'est pour ma situation étudiante.",
]


# ============================================================
# CONSTRUCTION DU DATASET
# ============================================================

def build_dataset():

    rows = []

    for label, seeds in SEEDS.items():

        # Les salutations ne doivent pas recevoir des préfixes
        # artificiels du type "Bonjour, Bonjour".
        if label == "salutation":

            for text in seeds:
                rows.append({
                    "text": text,
                    "semantic_intent": label,
                })

            extras = [
                "Salut ESIC",
                "Bonjour tout le monde",
                "Bonsoir assistant",
                "Merci pour votre aide",
                "Je vous remercie",
                "À plus tard",
                "Bonne continuation",
                "Bonne fin de journée",
                "Hey",
                "Hi",
                "Merci bien",
                "Bonjour, je suis étudiant",
                "Bonsoir ESIC",
                "Au revoir et merci",
                "À bientôt et merci",
                "Salut assistant",
            ]

            for text in extras:
                rows.append({
                    "text": text,
                    "semantic_intent": label,
                })

            continue

        for seed_index, seed in enumerate(seeds):

            for variant in range(5):

                prefix = PREFIXES[variant]

                suffix = SUFFIXES[
                    (seed_index + variant)
                    % len(SUFFIXES)
                ]

                text = (
                    f"{prefix}{seed}{suffix}"
                ).strip()

                rows.append({
                    "text": text,
                    "semantic_intent": label,
                })

    data = pd.DataFrame(rows)

    data = data.drop_duplicates(
        subset=[
            "text",
            "semantic_intent",
        ]
    )

    return data.sample(
        frac=1.0,
        random_state=42,
    ).reset_index(drop=True)


# ============================================================
# MODÈLE
# ============================================================

def build_pipeline():

    features = FeatureUnion([

        (
            "word",
            TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                strip_accents="unicode",
                sublinear_tf=True,
                min_df=1,
            ),
        ),

        (
            "char",
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                sublinear_tf=True,
                min_df=1,
            ),
        ),
    ])

    return Pipeline([

        (
            "features",
            features,
        ),

        (
            "classifier",
            LogisticRegression(
                max_iter=2500,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])


# ============================================================
# ENTRAÎNEMENT
# ============================================================

def main():

    data = build_dataset()

    data.to_csv(
        DATASET_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    counts = (
        data["semantic_intent"]
        .value_counts()
        .sort_index()
    )

    print(
        f"Dataset créé : {DATASET_PATH}"
    )

    print(
        f"Nombre d'exemples : {len(data)}"
    )

    print(
        "Nombre de classes : "
        f"{data['semantic_intent'].nunique()}"
    )

    print(counts.to_string())

    X_train, X_test, y_train, y_test = (
        train_test_split(
            data["text"],
            data["semantic_intent"],
            test_size=0.25,
            random_state=42,
            stratify=data["semantic_intent"],
        )
    )

    evaluation_model = build_pipeline()

    evaluation_model.fit(
        X_train,
        y_train,
    )

    predictions = (
        evaluation_model.predict(
            X_test
        )
    )

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    print(
        "\n===== ÉVALUATION HOLDOUT "
        "semantic_intent ====="
    )

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    print(
        f"Accuracy holdout : "
        f"{accuracy:.2%}"
    )

    # Modèle de production :
    # entraînement sur toutes les données.
    production_model = build_pipeline()

    production_model.fit(
        data["text"],
        data["semantic_intent"],
    )

    model_path = (
        MODEL_DIR
        / "semantic_intent_model.joblib"
    )

    joblib.dump(
        production_model,
        model_path,
    )

    labels = sorted(
        data["semantic_intent"]
        .unique()
        .tolist()
    )

    labels_path = (
        MODEL_DIR
        / "semantic_intent_labels.json"
    )

    labels_path.write_text(
        json.dumps(
            {
                "semantic_intents": labels,
                "count": len(labels),
                "training_examples": len(data),
                "holdout_accuracy": round(
                    float(accuracy),
                    4,
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"\nModèle enregistré : "
        f"{model_path}"
    )

    print(
        f"Étiquettes enregistrées : "
        f"{labels_path}"
    )

    if len(labels) != 15:
        raise RuntimeError(
            "15 classes attendues, "
            f"{len(labels)} obtenues."
        )

    if accuracy < 0.85:

        print(
            "ATTENTION : le holdout est "
            "sous le seuil de 85 %."
        )

    else:

        print(
            "OK : le holdout dépasse "
            "le seuil de 85 %."
        )


if __name__ == "__main__":
    main()