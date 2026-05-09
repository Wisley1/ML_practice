from typing import Any

from pydantic import BaseModel, Field

from app.schemas.user import LoyaltyStatusOut


class PredictionRequestBody(BaseModel):
    model_id: int = Field(..., ge=1)
    text: str = Field(..., min_length=1, max_length=50_000)


class PredictionOut(BaseModel):
    id: int
    status: str
    model_id: int
    result: dict[str, Any] | None
    error_message: str | None
    idempotency_key: str
    credits_charged: int | None = None
    loyalty: LoyaltyStatusOut | None = None
