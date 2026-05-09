from pydantic import BaseModel, ConfigDict


class MLModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    description: str | None
    model_type: str | None
    storage_path: str | None
    cost_credits_base: int | None
    is_active: bool | None
