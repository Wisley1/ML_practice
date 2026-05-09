from pydantic import BaseModel, EmailStr


class AdminUserRow(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    tier_name: str | None
    balance_credits: int
    predictions_completed_last_30_days: int
