"""Train category and intent classifiers for the ESIC assistant.

Expected location: backend/scripts/train_nlp_models.py
Expected dataset:  data/nlp_training.csv at the project root.
"""

from math import ceil
from pathlib import Path
import json

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BASE_DIR / "data" / "nlp_training.csv"
MODEL_DIR = BASE_DIR / "models" / "nlp"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def build_pipeline() -> Pipeline:
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
        ("features", features),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])


def train_target(data: pd.DataFrame, target: str) -> None:
    X = data["text"].astype(str)
    y = data[target].astype(str)
    model = build_pipeline()

    # A stratified holdout is only valid when both partitions can contain every
    # class. Tiny datasets still produce a usable model, but no fake test score.
    class_count = y.nunique()
    test_count = ceil(len(data) * 0.20)
    train_count = len(data) - test_count
    can_evaluate = (
        y.value_counts().min() >= 2
        and test_count >= class_count
        and train_count >= class_count
    )

    if can_evaluate:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y,
        )
        evaluation_model = build_pipeline()
        evaluation_model.fit(X_train, y_train)
        predictions = evaluation_model.predict(X_test)
        print(f"\n===== ÉVALUATION HOLDOUT : {target} =====")
        print(classification_report(y_test, predictions, zero_division=0))
    else:
        print(
            f"\n===== ÉVALUATION IGNORÉE : {target} =====\n"
            "Dataset trop petit pour séparer correctement toutes les classes. "
            "Ajoutez des exemples par classe pour obtenir une évaluation fiable."
        )

    # Train the saved production model on all available examples.
    model.fit(X, y)
    model_path = MODEL_DIR / f"{target}_model.joblib"
    joblib.dump(model, model_path)
    print(f"Modèle enregistré : {model_path}")


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset introuvable : {DATASET_PATH}\n"
            "Placez nlp_training.csv dans le dossier data/ à la racine du projet."
        )

    data = pd.read_csv(DATASET_PATH).dropna(subset=["text", "category", "intent"])
    data["text"] = data["text"].astype(str).str.strip()
    data = data[data["text"] != ""].copy()

    if data.empty:
        raise ValueError("Le dataset NLP ne contient aucune question exploitable.")

    for target in ("category", "intent"):
        if data[target].nunique() < 2:
            raise ValueError(f"Il faut au moins deux classes distinctes pour {target}.")
        counts = data[target].value_counts()
        if counts.min() < 2:
            raise ValueError(
                f"Chaque classe de {target} doit avoir au moins deux exemples. "
                f"Comptages actuels : {counts.to_dict()}"
            )

    for target in ("category", "intent"):
        train_target(data, target)

    labels = {
        "categories": sorted(data["category"].astype(str).unique().tolist()),
        "intents": sorted(data["intent"].astype(str).unique().tolist()),
        "training_examples": int(len(data)),
    }
    labels_path = MODEL_DIR / "labels.json"
    labels_path.write_text(
        json.dumps(labels, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Étiquettes enregistrées : {labels_path}")
    print("Entraînement terminé.")


if __name__ == "__main__":
    main()
