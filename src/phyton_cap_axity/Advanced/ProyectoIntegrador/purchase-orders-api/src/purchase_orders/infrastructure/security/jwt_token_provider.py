"""Adaptador: JwtTokenProvider.

Implementa el puerto `TokenProvider` usando `PyJWT`. Encapsula el secreto,
algoritmo y tiempo de expiración, evitando que la aplicación conozca
detalles de la librería concreta.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from purchase_orders.domain.exceptions.domain_exceptions import DomainError
from purchase_orders.domain.ports.token_provider import TokenPayload, TokenProvider


class InvalidTokenException(DomainError):
    """El token JWT es inválido, está mal formado o ha expirado."""

    def __init__(self) -> None:
        super().__init__("Token de acceso inválido o expirado.")


class JwtTokenProvider(TokenProvider):
    def __init__(
        self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 30
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def create_access_token(self, payload: TokenPayload) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=self._expire_minutes)
        claims = {
            "sub": str(payload.subject),
            "username": payload.username,
            "role": payload.role,
            "exp": expire,
            "iat": datetime.now(UTC),
        }
        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

    def decode(self, token: str) -> TokenPayload:
        try:
            claims = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except InvalidTokenError as exc:
            raise InvalidTokenException() from exc

        try:
            return TokenPayload(
                subject=UUID(claims["sub"]),
                username=claims["username"],
                role=claims["role"],
            )
        except (KeyError, ValueError) as exc:
            raise InvalidTokenException() from exc
