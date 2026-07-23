"""Configuración de la aplicación (Settings).

Centraliza todos los valores configurables vía variables de entorno,
usando `pydantic-settings`. Ningún otro módulo de infraestructura debe
leer `os.environ` directamente: todo pasa por aquí para tener una única
fuente de verdad y facilitar pruebas (override de settings).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Entorno
    environment: str = "development"
    debug: bool = False

    # Base de datos
    database_url: str = "sqlite+aiosqlite:///./purchase_orders.db"
    database_echo: bool = False

    # JWT / Seguridad
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # API
    api_title: str = "Purchase Orders API"
    api_version: str = "1.0.0"
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuración (cacheado por proceso)."""
    return Settings()
