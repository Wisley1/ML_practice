from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import torch

from app.ml.backend_peft import predict_peft_lora
from app.models.ml_models import MLModel


@patch("app.ml.backend_peft._get_classifier")
def test_predict_peft_lora_softmax_and_id2label(mock_get):
    tokenizer = MagicMock(
        return_value={
            "input_ids": torch.tensor([[101, 102]]),
            "attention_mask": torch.tensor([[1, 1]]),
        }
    )
    torch_model = MagicMock()
    torch_model.config = SimpleNamespace(
        id2label={0: "neutral", 1: "positive", 2: "negative"}
    )
    torch_model.return_value = SimpleNamespace(logits=torch.tensor([[0.1, 0.2, 5.0]]))
    mock_get.return_value = (tokenizer, torch_model)

    ml = MLModel(
        id=7,
        name="rubert",
        description="d",
        model_type="peft_lora",
        storage_path="seara/rubert-tiny2-russian-sentiment",
        cost_credits_base=5,
        extra_metadata=None,
        is_active=True,
    )

    out = predict_peft_lora(
        "seara/rubert-tiny2-russian-sentiment", "тест отзыва", ml
    )

    assert out["label"] == "negative"
    assert out["score"] > 0.95
    assert out["model_id"] == 7
    assert out["backend"] == "hf_sequence_classification"
    tokenizer.assert_called_once()
