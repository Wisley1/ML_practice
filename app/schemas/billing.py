from pydantic import BaseModel, Field


class MockTopUpBody(BaseModel):
    credits_to_add: int = Field(..., gt=0, description="Credits to add")


class MockTopUpResponse(BaseModel):
    payment_id: int = Field(..., description="Payment row id")
    balance_credits: int = Field(..., description="Wallet balance after top-up")
