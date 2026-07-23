"""Caso de uso: Login (autenticación) — emite un token de acceso JWT.

Coordina tres puertos: `UserRepository` (buscar credenciales),
`PasswordHasher` (verificar contraseña) y `TokenProvider` (emitir el JWT).
Ninguno de estos puertos revela detalles de PyJWT/bcrypt a este caso de uso.
"""

from __future__ import annotations

from purchase_orders.application.dtos.common_dto import LoginCommand, TokenResult
from purchase_orders.application.exceptions import InvalidCredentialsError
from purchase_orders.domain.ports.password_hasher import PasswordHasher
from purchase_orders.domain.ports.token_provider import TokenPayload, TokenProvider
from purchase_orders.domain.ports.unit_of_work import UnitOfWork


class LoginUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        password_hasher: PasswordHasher,
        token_provider: TokenProvider,
    ) -> None:
        self._uow = uow
        self._password_hasher = password_hasher
        self._token_provider = token_provider

    async def execute(self, command: LoginCommand) -> TokenResult:
        async with self._uow as uow:
            user = await uow.users.get_by_username(command.username)
            if user is None or not user.is_active:
                raise InvalidCredentialsError()

            if not self._password_hasher.verify(command.password, user.hashed_password):
                raise InvalidCredentialsError()

            token = self._token_provider.create_access_token(
                TokenPayload(subject=user.id, username=user.username, role=user.role)
            )
            return TokenResult(access_token=token)
