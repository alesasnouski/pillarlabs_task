from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    bcrypt_rounds: int = 12

    model_config = {"env_file": ".env"}


settings = Settings()
