"""Deterministic text cleanup shared by training and offline inference."""
import re
import unicodedata


def normalize_ticket_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    # Explicitly quoted resolved correspondence is background, not a fresh complaint.
    text = re.split(r"on an earlier date,?\s+the support desk wrote:", text)[0]
    text = re.sub(r"(?m)^\s*>.*$", " ", text)
    # Synthetic reference IDs carry no issue meaning and differ across splits.
    text = re.sub(r"\bsim[a-z]-[a-z0-9]+\b", " reference ", text)
    return re.sub(r"\s+", " ", text).strip()
