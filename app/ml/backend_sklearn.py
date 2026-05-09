from __future__ import annotations

import logging
import re
from pathlib import Path

import joblib
import numpy as np
from huggingface_hub import hf_hub_download

logger = logging.getLogger(__name__)

_pipeline_cache: dict[str, object] = {}
_hf_dual_cache: dict[str, tuple[object, object]] = {}

_HF_REPO_ID_RE = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*/[a-zA-Z0-9][a-zA-Z0-9_.-]*$"
)


def _is_huggingface_repo_ref(storage_path: str) -> bool:
    s = storage_path.strip()
    if not s or s.startswith(("/", "./", "../", "~")):
        return False
    if s.endswith((".joblib", ".pkl", ".pickle")):
        return False
    if Path(s).is_file():
        return False
    return bool(_HF_REPO_ID_RE.match(s))


def load_sklearn_pipeline(storage_path: str):
    p = Path(storage_path)
    if not p.is_file():
        raise FileNotFoundError(f"нет файла: {storage_path}")
    if storage_path not in _pipeline_cache:
        _pipeline_cache[storage_path] = joblib.load(storage_path)
    return _pipeline_cache[storage_path]


def _load_hf_tfidf_svm(repo_id: str) -> tuple[object, object]:
    if repo_id not in _hf_dual_cache:
        logger.info("Loading HF sklearn TF-IDF + SVM: %s", repo_id)
        clf_path = hf_hub_download(
            repo_id, filename="sklearn_model.joblib", repo_type="model"
        )
        vec_path = hf_hub_download(
            repo_id, filename="vectorizer_model.joblib", repo_type="model"
        )
        clf = joblib.load(clf_path)
        vectorizer = joblib.load(vec_path)
        _hf_dual_cache[repo_id] = (vectorizer, clf)
    return _hf_dual_cache[repo_id]


def _class_probabilities_row(clf: object, X) -> tuple[dict[str, float] | None, float | None]:
    if not hasattr(clf, "predict_proba"):
        return None, None
    row = np.asarray(clf.predict_proba(X))[0]
    classes = getattr(clf, "classes_", None)
    if classes is None or len(classes) != len(row):
        return None, float(np.max(row))
    d = {str(c): float(p) for c, p in zip(classes, row)}
    return d, float(np.max(row))


def _score_from_classifier(clf: object, X) -> float | None:
    if hasattr(clf, "predict_proba"):
        return float(np.max(clf.predict_proba(X)))
    if hasattr(clf, "decision_function"):
        df = np.asarray(clf.decision_function(X))
        if df.ndim == 1:
            z = float(df[0])
            return float(1.0 / (1.0 + np.exp(-z)))
        row = df[0]
        ex = np.exp(row - np.max(row))
        probs = ex / np.sum(ex)
        return float(np.max(probs))
    return None


def predict_sklearn_tfidf(storage_path: str, text: str) -> dict:
    path = storage_path.strip()
    if _is_huggingface_repo_ref(path):
        return _predict_hf_dual(path, text)

    pipe = load_sklearn_pipeline(path)
    label = pipe.predict([text])[0]
    proba_dict, proba_max = _class_probabilities_row(pipe, [text])
    score = proba_max if proba_max is not None else _score_from_classifier(pipe, [text])
    out: dict = {"label": str(label), "score": score, "backend": "sklearn_tfidf"}
    if proba_dict:
        out["class_probabilities"] = proba_dict
    return out


def _predict_hf_dual(repo_id: str, text: str) -> dict:
    vectorizer, clf = _load_hf_tfidf_svm(repo_id)
    cleaned = text.lower()
    X = vectorizer.transform([cleaned])
    label = clf.predict(X)[0]
    proba_dict, proba_max = _class_probabilities_row(clf, X)
    score = proba_max if proba_max is not None else _score_from_classifier(clf, X)
    out: dict = {
        "label": str(label),
        "score": score,
        "backend": "sklearn_tfidf_hf",
        "hf_model_ref": repo_id,
    }
    if proba_dict:
        out["class_probabilities"] = proba_dict
    return out
