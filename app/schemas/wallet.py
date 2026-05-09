from pydantic import BaseModel


class WalletOut(BaseModel):
    user_id: int
    balance_credits: int
