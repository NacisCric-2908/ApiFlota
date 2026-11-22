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

    # APIs de terceros (gratuitas y sin llave). Ver docs/terceros.md.
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    nominatim_url: str = "https://nominatim.openstreetmap.org/reverse"
    # Nominatim exige un User-Agent que identifique la aplicación (sin datos personales).
    externos_user_agent: str = "ApiFlota-ClusterRodar/0.1"
    externos_timeout_s: float = 3.0  # tiempo máximo de espera por intento
    externos_reintentos: int = 2  # reintentos tras el primer intento (máx. 3 intentos)
    externos_backoff_s: float = 0.2  # espera inicial entre intentos; se duplica cada vez
    nominatim_intervalo_s: float = 1.1  # su política: máximo 1 petición por segundo


@lru_cache
def get_settings() -> Settings:
    return Settings()
