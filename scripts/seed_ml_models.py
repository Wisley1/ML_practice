from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.ml_models import MLModel


def seed_ml_models() -> None:
    db: Session = SessionLocal()
    try:
        exists = db.scalars(select(MLModel).limit(1)).first()
        if exists is not None:
            return
        models = [
            MLModel(
                owner_id=None,
                name="tfidf_svm_en_sentiment",
                description=(
                    "TF-IDF + Linear SVM (HF: DineshKumar1329/Sentiment_Analysis)"
                ),
                model_type="sklearn_tfidf",
                storage_path="DineshKumar1329/Sentiment_Analysis",
                cost_credits_base=1,
                extra_metadata=None,
                is_active=True,
            ),
            MLModel(
                owner_id=None,
                name="rubert_tiny2_ru_financial_sentiment",
                description=(
                    "RuBERT-tiny2, финансовый сентимент RU (~29M params; "
                    "HF: mxlcw/rubert-tiny2-russian-financial-sentiment)"
                ),
                model_type="embeddings_sklearn",
                storage_path="mxlcw/rubert-tiny2-russian-financial-sentiment",
                cost_credits_base=2,
                extra_metadata=None,
                is_active=True,
            ),
            MLModel(
                owner_id=None,
                name="rubert_tiny2_ru_sentiment",
                description=(
                    "RuBERT-tiny2 Russian sentiment (HF: seara/rubert-tiny2-russian-sentiment)"
                ),
                model_type="peft_lora",
                storage_path="seara/rubert-tiny2-russian-sentiment",
                cost_credits_base=5,
                extra_metadata=None,
                is_active=True,
            ),
        ]
        db.add_all(models)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_ml_models()
