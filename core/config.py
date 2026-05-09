from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(..., env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(..., env='ACCESS_TOKEN_EXPIRE_MINUTES')
    max_review_chars: int = Field(..., env='MAX_REVIEW_CHARS')
    max_model_upload_mb: int = Field(..., env='MAX_MODEL_UPLOAD_MB')
    allowed_lora_bases: str = Field(..., env='ALLOWED_LORA_BASES')
    model_storage_path: str = Field(..., env="MODEL_STORAGE_PATH")
    celery_broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_RESULT_BACKEND",
    )
    admin_bootstrap_emails: str = Field(default="")

settings = Settings()