"""
Classifier interface (Person B / Engineering)

Loads Person A's trained model the moment model/artifacts/classifier.joblib
exists; falls back to a rule-only stub until then so the pipeline is never
blocked waiting on Phase 1. main_pipeline.py always calls classify(record) —
callers never need to know which path ran.
"""
import os
import re
from typing import Tuple

from parser import FEATURE_COLUMNS, ElementRecord

# --- Must match model/feature_spec.md LABEL_MAP exactly ---
LABEL_MAP = {
    0: "Title", 1: "Author", 2: "Chapter Heading", 3: "Subheading",
    4: "Body Paragraph", 5: "Table", 6: "Figure", 7: "Caption",
    8: "Reference", 9: "List",
}
LABEL_TO_ID = {v: k for k, v in LABEL_MAP.items()}

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "model", "artifacts")

_MODEL = None
_SCALER = None
_MODEL_LOAD_ATTEMPTED = False


def load_real_model() -> bool:
    """Try to load Person A's trained model + scaler. Returns True if loaded."""
    global _MODEL, _SCALER, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL is not None
    _MODEL_LOAD_ATTEMPTED = True

    clf_path = os.path.join(ARTIFACT_DIR, "classifier.joblib")
    scaler_path = os.path.join(ARTIFACT_DIR, "scaler.joblib")
    if not os.path.exists(clf_path):
        print("[classifier] No classifier.joblib found in model/artifacts/ "
              "-- using rule-based stub. Drop the trained model there to switch over.")
        return False

    import joblib
    _MODEL = joblib.load(clf_path)
    _SCALER = joblib.load(scaler_path) if os.path.exists(scaler_path) else None
    print(f"[classifier] Loaded trained model from {clf_path}"
          + (" (with scaler)" if _SCALER is not None else " (no scaler found)"))
    return True


def _heuristic_guess(text: str, feat: dict) -> Tuple[str, float]:
    """Phase-1 stub / fallback when no trained model is present yet.
    Mirrors `heuristic_guess()` in Person A's notebook (Section 3) so
    behaviour is consistent even before the real model exists."""
    t = text.strip()
    if feat["is_table_element"]:
        return "Table", 0.99
    if feat["has_image"]:
        return "Figure", 0.99
    if re.match(r"^(figure|fig\.)\s*\d+", t, re.I) or re.match(r"^table\s*\d+", t, re.I):
        return "Caption", 0.9
    if feat["position_ratio_in_doc"] < 0.02 and feat["font_size"] >= 16:
        return "Title", 0.85
    if re.match(r"^(chapter|section)\s+\d+", t, re.I):
        return "Chapter Heading", 0.9
    if feat["starts_with_number"] and feat["word_count"] < 8:
        return "List", 0.7
    if re.match(r"^\[?\d+\]?\s", t) and feat["word_count"] > 8:
        return "Reference", 0.75
    if feat["is_bold"] and feat["font_size"] < 16 and feat["word_count"] < 12:
        return "Subheading", 0.6
    return "Body Paragraph", 0.5


def rule_based_override(text: str, has_image: int, is_table_element: int,
                         ml_label: str, ml_confidence: float,
                         threshold: float = 0.55) -> str:
    """High-confidence overrides on top of the ML/heuristic output.
    Ported verbatim from Person A's notebook Section 7 (rule_based_override)
    -- keep the two in sync if either side changes."""
    if is_table_element:
        return "Table"
    if has_image:
        return "Figure"
    t = text.strip()
    if re.match(r"^chapter\s+\d+", t, re.I):
        return "Chapter Heading"
    if re.match(r"^\[?\d+\]?\s", t) and len(t.split()) > 8:
        return "Reference"
    if re.match(r"^(figure|fig\.)\s*\d+", t, re.I):
        return "Caption"
    if re.match(r"^table\s*\d+", t, re.I):
        return "Caption"
    if ml_confidence < threshold:
        return ml_label  # not confident enough to override, but flag for review
    return ml_label


def classify(record: ElementRecord) -> Tuple[str, float]:
    """Single-element convenience wrapper. Fine for a few elements or
    interactive use (see scripts/compare_before_after.py). For a whole
    document, use classify_batch() instead -- calling the model one row at
    a time is >1000x slower than one batched call (measured: ~65s vs
    ~0.06s for 4,675 rows) because every .predict()/.predict_proba() call
    pays fixed sklearn/joblib overhead (input validation, tag lookup,
    parallel dispatch) regardless of batch size."""
    return classify_batch([record])[0]


def classify_batch(records) -> list:
    """Classify many elements in one shot. Returns a list of
    (label_name, confidence) tuples, same order as `records`.

    This is what main_pipeline.py calls -- one matrix, one predict() call,
    one predict_proba() call, no matter how many thousand elements are in
    the document.
    """
    have_model = load_real_model()
    n = len(records)
    if n == 0:
        return []

    feats = [dict(zip(FEATURE_COLUMNS, r.features)) for r in records]

    if have_model:
        import numpy as np
        X = np.array([r.features for r in records], dtype=float)
        if _SCALER is not None:
            X = _SCALER.transform(X)
        pred_ids = _MODEL.predict(X)
        labels = [LABEL_MAP.get(int(pid), "Body Paragraph") for pid in pred_ids]
        if hasattr(_MODEL, "predict_proba"):
            proba = _MODEL.predict_proba(X)
            confidences = proba.max(axis=1).tolist()
        else:
            confidences = [0.75] * n
    else:
        guesses = [_heuristic_guess(r.text, f) for r, f in zip(records, feats)]
        labels = [g[0] for g in guesses]
        confidences = [g[1] for g in guesses]

    results = []
    for record, feat, label, confidence in zip(records, feats, labels, confidences):
        final_label = rule_based_override(
            record.text, feat["has_image"], feat["is_table_element"], label, confidence
        )
        results.append((final_label, confidence))
    return results
