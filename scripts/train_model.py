import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.model import MODEL_VERSION, TicketModel, compose_text, make_classifier  # noqa: E402

DATA_DIR = ROOT / "datasets"
ARTIFACT_DIR = ROOT / "artifacts"
SECONDARY_NONE = "__none__"


def read_examples(path: Path) -> Tuple[List[Dict[str, str]], List[str], List[str], List[str]]:
    tickets: List[Dict[str, str]] = []
    categories: List[str] = []
    secondary_categories: List[str] = []
    urgent_labels: List[str] = []
    with path.open("r", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            tickets.append(
                {
                    "channel": row["channel"],
                    "subject": row["subject"],
                    "text": row["text"],
                }
            )
            categories.append(row["category"])
            secondary_categories.append(row["secondary_category"] or SECONDARY_NONE)
            urgent_labels.append(row["is_urgent"].strip().lower())
    return tickets, categories, secondary_categories, urgent_labels


def evaluate(labels: List[str], predictions: List[str]) -> Dict[str, float]:
    return {
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "macro_f1": round(float(f1_score(labels, predictions, average="macro")), 4),
    }


def main() -> None:
    train_tickets, train_categories, train_secondary, train_urgent = read_examples(
        DATA_DIR / "train.csv"
    )
    validation_tickets, validation_categories, validation_secondary, validation_urgent = (
        read_examples(DATA_DIR / "validation.csv")
    )
    train_texts = [compose_text(ticket) for ticket in train_tickets]
    category_model = make_classifier(
        C=40.0,
        class_weight="balanced",
        char_analyzer="char_wb",
        char_ngram_range=(2, 6),
    ).fit(train_texts, train_categories)
    secondary_model = make_classifier().fit(train_texts, train_secondary)
    urgent_model = make_classifier().fit(train_texts, train_urgent)

    artifact = {
        "model_version": MODEL_VERSION,
        "category_model": category_model,
        "secondary_model": secondary_model,
        "urgent_model": urgent_model,
    }
    classifier = TicketModel(artifact)
    validation_predictions = classifier.predict_many(validation_tickets)
    metrics = {
        "model_version": MODEL_VERSION,
        "training_examples": len(train_tickets),
        "validation_examples": len(validation_tickets),
        "validation": {
            "category": evaluate(
                validation_categories,
                [prediction["category"] for prediction in validation_predictions],
            ),
            "secondary_category": evaluate(
                validation_secondary,
                [
                    prediction["secondary_category"] or SECONDARY_NONE
                    for prediction in validation_predictions
                ],
            ),
            "is_urgent": evaluate(
                [row.strip().lower() for row in validation_urgent],
                [
                    "true" if prediction["is_urgent"] else "false"
                    for prediction in validation_predictions
                ],
            ),
        },
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        artifact,
        ARTIFACT_DIR / "model.joblib",
        compress=3,
    )
    (ARTIFACT_DIR / "evaluation_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))
    print("Saved model to {}".format(ARTIFACT_DIR / "model.joblib"))


if __name__ == "__main__":
    main()
