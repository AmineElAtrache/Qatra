from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://qatra:qatra@localhost:5432/qatra"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    engine_version: str = "0.1.0"
    cors_origins: str = "http://localhost:3000"

    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    knowledge_dir: str = "knowledge"
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    notification_channel: str = "web"
    speech_backend: str = "webspeech"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
