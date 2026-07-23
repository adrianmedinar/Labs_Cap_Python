"""Puerto (interfaz): TokenProvider.

Abstrae la emisión y validación de tokens de acceso (JWT u otro esquema).
La capa de aplicación depende de este contrato; la implementación concreta
con `python-jose`/`pyjwt` vive en infraestructura.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TokenPayload:
    subject: UUID
    username: str
    role: str


class TokenProvider(ABC):
    @abstractmethod
    def create_access_token(self, payload: TokenPayload) -> str:
        """Genera un token de acceso firmado con expiración configurada."""

    @abstractmethod
    def decode(self, token: str) -> TokenPayload:
        """Decodifica y valida un token. Lanza excepción si es inválido/expiró."""
