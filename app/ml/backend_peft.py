import logging
from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.models.ml_models import MLModel

logger = logging.getLogger(__name__)

# https://huggingface.co/seara/rubert-tiny2-russian-sentiment
_classifier_cache: dict[str, tuple[Any, Any]] = {}


def _get_classifier(model_ref: str) -> tuple[Any, Any]:
    if model_ref not in _classifier_cache:
        logger.info("Loading HF classifier: %s", model_ref)
        tokenizer = AutoTokenizer.from_pretrained(model_ref)
        torch_model = AutoModelForSequenceClassification.from_pretrained(model_ref)
        torch_model.eval()
        _classifier_cache[model_ref] = (tokenizer, torch_model)
    return _classifier_cache[model_ref]


def _label_from_config(config: Any, idx: int) -> str:
    mapping = getattr(config, "id2label", None) or {}
    raw = mapping.get(idx, mapping.get(str(idx)))
    return str(raw) if raw is not None else str(idx)


def predict_peft_lora(storage_path: str, text: str, ml_model: MLModel) -> dict:
    tokenizer, torch_model = _get_classifier(storage_path.strip())
    enc = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=False,
    )
    with torch.no_grad():
        logits = torch_model(**enc).logits
        probs = torch.softmax(logits, dim=-1)[0]
    idx = int(probs.argmax().item())
    score = float(probs[idx].item())
    label = _label_from_config(torch_model.config, idx)
    id2label = getattr(torch_model.config, "id2label", None) or {}
    class_probabilities: dict[str, float] = {}
    for i in range(probs.shape[0]):
        lab = id2label.get(i, id2label.get(str(i), str(i)))
        class_probabilities[str(lab)] = float(probs[i].item())
    return {
        "label": label,
        "score": score,
        "model_id": ml_model.id,
        "model_name": ml_model.name,
        "model_type": ml_model.model_type,
        "backend": "hf_sequence_classification",
        "hf_model_ref": storage_path.strip(),
        "class_probabilities": class_probabilities,
    }
