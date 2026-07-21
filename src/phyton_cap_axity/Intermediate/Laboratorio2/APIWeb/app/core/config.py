"""
Configuración central de la aplicación.
Usa pydantic-settings para cargar variables de entorno de forma tipada y validada.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Metadata de la API (se refleja en OpenAPI/docs) ---
    PROJECT_NAME: str = "Orders API"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # --- Base de datos ---
    # Por defecto SQLite async local; en tests se sobreescribe por una BD en memoria.
    DATABASE_URL: str = "sqlite+aiosqlite:///./orders.db"

    # --- JWT ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_super_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Cachea la instancia de settings para no releer el .env en cada request."""
    return Settings()


settings = get_settings()
