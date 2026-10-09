import unicodedata
import re
from pathlib import Path
from typing import Any, Dict, List

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.svm import LinearSVC
from app.preprocessing import normalize_ticket_text

MODEL_VERSION = "tf-phase2-drive-2.1.0"
MODEL_PATH = Path(__file__).resolve().parent.parent / "artifacts" / "model.joblib"
URGENT_THRESHOLD = 0.2
SECONDARY_THRESHOLD = 0.1

TEAM_BY_CATEGORY = {
    "payment_refund": "Payments & Refunds",
    "ride_trip_issue": "Ride Operations",
    "lost_item": "Lost & Found",
    "order_missing_wrong": "Food Operations",
    "delivery_delay": "Delivery Operations",
    "food_quality": "Restaurant Quality",
    "account_promo": "Account Services",
    "safety_conduct": "Trust & Safety",
    "app_technical": "Tech Support",
    "general_inquiry": "Front-line Support",
    "spam_irrelevant": "Auto-close / Spam Filter",
}


def compose_text(ticket: Dict[str, Any]) -> str:
    channel = ticket.get("channel", "")
    language = ticket.get("language", "")
    subject = ticket.get("subject", "")
    text = ticket.get("text", "")
    combined = "{} language {}\n{}\n{}".format(channel, language, subject, text)
    return unicodedata.normalize("NFC", combined)


def make_classifier(
    C: float = 3.0,
    class_weight: Any = None,
    char_analyzer: str = "char",
    char_ngram_range: tuple = (2, 5),
    estimator: str = "logistic_regression",
    normalize: bool = False,
) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=150000,
                    sublinear_tf=True,
                    preprocessor=normalize_ticket_text if normalize else None,
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer=char_analyzer,
                    ngram_range=tuple(char_ngram_range),
                    min_df=2,
                    max_features=300000,
                    sublinear_tf=True,
                    preprocessor=normalize_ticket_text if normalize else None,
                ),
            ),
        ]
    )
    return Pipeline(
        [
            ("features", features),
            (
                "classifier",
                CalibratedClassifierCV(
                    estimator=LinearSVC(C=C, class_weight=class_weight, max_iter=5000,
                                        random_state=42, dual=True),
                    method="sigmoid", cv=3,
                ) if estimator == "calibrated_svm" else LogisticRegression(
                    C=C,
                    class_weight=class_weight,
                    max_iter=300,
                    random_state=42,
                ),
            ),
        ]
    )


class TicketModel:
    def __init__(self, artifact: Dict[str, Any]) -> None:
        if artifact.get("model_version") != MODEL_VERSION:
            raise ValueError("Model artifact version does not match application version.")
        self.category_model = artifact["category_model"]
        self.secondary_model = artifact["secondary_model"]
        self.urgent_model = artifact["urgent_model"]
        self.urgent_threshold = artifact.get("urgent_threshold", URGENT_THRESHOLD)
        self.secondary_threshold = artifact.get("secondary_threshold", SECONDARY_THRESHOLD)
        self.training_metadata = artifact.get("training_metadata", {})

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "TicketModel":
        if not path.is_file():
            raise FileNotFoundError(
                "Trained model artifact is missing. Run `python scripts/train_model.py`."
            )
        return cls(joblib.load(path))

    def predict_many(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self._infer_many(tickets)

    def analyze_many(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self._infer_many(tickets, include_details=True)

    def _infer_many(self, tickets: List[Dict[str, Any]], include_details: bool = False) -> List[Dict[str, Any]]:
        if not tickets:
            return []
        texts = [compose_text(ticket) for ticket in tickets]
        category_probabilities = self.category_model.predict_proba(texts)
        secondary_probabilities = self.secondary_model.predict_proba(texts)
        urgent_probabilities = self.urgent_model.predict_proba(texts)
        category_labels = self.category_model.named_steps["classifier"].classes_
        secondary_labels = self.secondary_model.named_steps["classifier"].classes_
        urgent_labels = list(self.urgent_model.named_steps["classifier"].classes_)
        urgent_true_index = urgent_labels.index("true")

        predictions = []
        for index, ticket in enumerate(tickets):
            primary_index = int(category_probabilities[index].argmax())
            category = str(category_labels[primary_index])
            secondary_candidates = [
                candidate
                for candidate, label in enumerate(secondary_labels)
                if label not in ("__none__", category)
            ]
            secondary_index = max(
                secondary_candidates,
                key=lambda candidate: secondary_probabilities[index][candidate],
                default=None,
            )
            secondary = None
            if (
                secondary_index is not None
                and secondary_probabilities[index][secondary_index] >= self.secondary_threshold
            ):
                secondary = str(secondary_labels[secondary_index])

            raw_category, raw_secondary = category, secondary

            category, secondary = self._apply_precedence(
                normalize_ticket_text(compose_text(ticket)), category, secondary
            )
            confidence_index = list(category_labels).index(category)
            confidence = float(category_probabilities[index][confidence_index])
            is_urgent = (
                urgent_probabilities[index][urgent_true_index] >= self.urgent_threshold
            )
            if category == "spam_irrelevant":
                secondary = None
                is_urgent = False

            prediction = {
                "category": category,
                "secondary_category": secondary,
                "team": TEAM_BY_CATEGORY[category],
                "is_urgent": bool(is_urgent),
                "confidence": max(0.0, min(1.0, confidence)),
                "model_version": MODEL_VERSION,
                "needs_human_review": confidence < 0.5 or len(ticket["text"].split()) <= 3,
            }
            if "ticket_id" in ticket:
                prediction["ticket_id"] = ticket["ticket_id"]
            if include_details:
                def ranked(labels, values):
                    return sorted([{"label": str(name), "probability": float(value)}
                                   for name, value in zip(labels, values)],
                                  key=lambda item: item["probability"], reverse=True)
                reasons = []
                if confidence < 0.5:
                    reasons.append("Primary confidence below 50%")
                if len(ticket["text"].split()) <= 3:
                    reasons.append("Message has three or fewer words")
                if is_urgent:
                    reasons.append("Urgent ticket requires support attention")
                predictions.append({"prediction": prediction, "analysis": {
                    "primary_candidates": ranked(category_labels, category_probabilities[index]),
                    "secondary_candidates": ranked(secondary_labels, secondary_probabilities[index]),
                    "urgent_probability": float(urgent_probabilities[index][urgent_true_index]),
                    "urgent_threshold": self.urgent_threshold,
                    "secondary_threshold": self.secondary_threshold,
                    "raw_category": raw_category,
                    "rule_adjusted": category != raw_category or secondary != raw_secondary,
                    "review_reasons": reasons,
                    "model_version": MODEL_VERSION,
                }})
            else:
                predictions.append(prediction)
        return predictions

    @staticmethod
    def _apply_precedence(
        text: str, category: str, secondary: Any
    ) -> tuple:
        normalized = text.lower()
        resolved_background = bool(
            re.search(
                r"\b(?:already resolved|was resolved|has been resolved|issue is resolved|"
                r"problem was fixed|already fixed|case closed|no longer happening)\b",
                normalized,
            )
        )
        active_safety = not resolved_background and (
            (
                re.search(
                    r"\bdriver\b.{0,140}\b(?:not stopping|isn't stopping|won't stop|"
                    r"refuses? to stop)\b",
                    normalized,
                )
                and re.search(r"\b(?:scared|afraid|trapped|inside the car)\b", normalized)
            )
            or (
                "රියදුරා" in normalized
                and any(
                    phrase in normalized
                    for phrase in ("නවත්තන්නේ නැහැ", "මට බයයි")
                )
            )
            or (
                "driver" in normalized
                and any(
                    phrase in normalized
                    for phrase in ("nawaththanne na", "mata bayai")
                )
            )
            or (
                "driver" in normalized
                and any(
                    phrase in normalized
                    for phrase in ("பயமாக", "நிறுத்தவில்லை")
                )
            )
        )
        refund_requested = bool(
            re.search(r"\b(?:refund|money back|refund ekak)\b", normalized)
            or any(phrase in normalized for phrase in ("பணம் திருப்பி", "මුදල් ආපසු"))
        )
        missing_item = bool(
            re.search(
                r"\b(?:item|items|drink|food|meal|dish|part|portion|contents?)\b"
                r"[\s\S]{0,55}\b(?:missing|absent|not included|not in the bag|never came)\b"
                r"|\bmissing item\b|\bhalf the items\b",
                normalized,
            )
            or "ஐட்டம் வரல" in normalized
            or "item varala" in normalized
            or (
                any(word in normalized for word in ("parcel eka", "packet eka", "order eka"))
                and any(phrase in normalized for phrase in ("athule na", "athule nathi"))
            )
        )
        current_missing_item = bool(
            re.search(
                r"\b(?:now|currently|today|new issue)\b[\s\S]{0,120}"
                r"\b(?:missing|absent|not included)\b",
                normalized,
            )
        )
        delayed = bool(
            re.search(r"\b(?:late|delayed|delay|still waiting)\b", normalized)
            or any(phrase in normalized for phrase in ("தாமத", "පරක්කු"))
        )

        if active_safety:
            category = "safety_conduct"
        elif missing_item and (not resolved_background or current_missing_item):
            category = "order_missing_wrong"
            if refund_requested:
                secondary = "payment_refund"
        elif delayed and refund_requested:
            category = "delivery_delay"
            secondary = "payment_refund"

        if secondary == category:
            secondary = None
        return category, secondary
