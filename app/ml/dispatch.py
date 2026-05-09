from app.ml.stub import predict_stub
from app.ml.backend_sklearn import predict_sklearn_tfidf
from app.ml.backend_peft import predict_peft_lora
from app.models.ml_models import MLModel

TYPE_SKLEARN = "sklearn_tfidf"
TYPE_EMB = "embeddings_sklearn"
TYPE_PEFT = "peft_lora"


def predict_with_model(model: MLModel, text: str) -> dict:
    mt = (model.model_type or "").strip()
    path = model.storage_path or ""

    if mt == TYPE_SKLEARN:
        if not path:
            return predict_stub(text, model)
        return predict_sklearn_tfidf(path, text)

    if mt == TYPE_EMB:
        if not path:
            return predict_stub(text, model)
        return predict_peft_lora(path, text, model)

    if mt == TYPE_PEFT:
        if not path:
            return predict_stub(text, model)
        return predict_peft_lora(path, text, model)

    return predict_stub(text, model)
