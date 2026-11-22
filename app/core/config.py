from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída de variables de entorno. Sin valores por defecto para lo sensible."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str
    mongo_db: str = "flota"
    gateway_secret: str
    seed_on_empty: bool = True
    log_level: str = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
