"""Evaluate the saved artifact without retraining or changing its thresholds."""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.model import MODEL_VERSION, TEAM_BY_CATEGORY, TicketModel  # noqa: E402
from scripts.train_model import evaluate, read_examples  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "datasets/validation.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/evaluation_breakdown.json")
    args = parser.parse_args()
    tickets, categories, secondary, urgent = read_examples(args.dataset)
    with args.dataset.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    predictions = TicketModel.load().predict_many(tickets)
    predicted_categories = [p["category"] for p in predictions]
    labels = list(TEAM_BY_CATEGORY)
    groups = {}
    for language in sorted({row["language"] for row in rows}):
        indices = [i for i, row in enumerate(rows) if row["language"] == language]
        groups[language] = {
            "count": len(indices),
            **evaluate([categories[i] for i in indices], [predicted_categories[i] for i in indices]),
        }
    confusions = Counter((actual, predicted) for actual, predicted in zip(categories, predicted_categories) if actual != predicted)
    report = {
        "model_version": MODEL_VERSION,
        "dataset": args.dataset.name,
        "examples": len(tickets),
        "evaluation_note": "Development validation data informed model selection and thresholds; this is not an independent test score.",
        "validation": {
            "category": evaluate(categories, predicted_categories),
            "secondary_category": evaluate(secondary, [p["secondary_category"] or "__none__" for p in predictions]),
            "is_urgent": evaluate(urgent, [str(p["is_urgent"]).lower() for p in predictions]),
        },
        "category_report": classification_report(categories, predicted_categories, labels=labels, output_dict=True, zero_division=0),
        "category_confusion_matrix": {"labels": labels, "rows_actual_columns_predicted": confusion_matrix(categories, predicted_categories, labels=labels).tolist()},
        "category_by_language": groups,
        "top_category_confusions": [{"actual": a, "predicted": p, "count": n} for (a, p), n in confusions.most_common(10)],
        "human_review_count": sum(p["needs_human_review"] for p in predictions),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["validation"], indent=2))
    print("Saved evaluation breakdown to {}".format(args.output))


if __name__ == "__main__":
    main()
