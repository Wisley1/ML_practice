from app.models.ml_models import MLModel


def predict_stub(text: str, model: MLModel) -> dict:
    lowered = text.lower().strip()
    if any(w in lowered for w in ("bad", "ужас", "negative", "hate")):
        label = "negative"
        score = 0.86
    else:
        label = "positive"
        score = 0.81
    return {
        "label": label,
        "score": score,
        "model_id": model.id,
        "model_name": model.name,
        "model_type": model.model_type,
    }
