from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class LoyaltyStatusOut(BaseModel):
    tier_name: str | None = None
    discount_percentage: int | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime | None
    loyalty: LoyaltyStatusOut
