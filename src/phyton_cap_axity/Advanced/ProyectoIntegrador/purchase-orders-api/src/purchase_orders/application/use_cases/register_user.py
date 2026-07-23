"""Caso de uso: Registrar Usuario.

Depende de los puertos `UserRepository` y `PasswordHasher`. Nunca conoce
el algoritmo de hashing concreto (bcrypt/argon2) ni la tecnología de
persistencia: solo conoce los contratos del dominio.
"""

from __future__ import annotations

from purchase_orders.application.dtos.common_dto import (
    RegisterUserCommand,
    UserResult,
)
from purchase_orders.application.exceptions import UsernameAlreadyExistsError
from purchase_orders.application.mappers import user_to_result
from purchase_orders.domain.entities.user import User
from purchase_orders.domain.ports.password_hasher import PasswordHasher
from purchase_orders.domain.ports.unit_of_work import UnitOfWork


class RegisterUserUseCase:
    def __init__(self, uow: UnitOfWork, password_hasher: PasswordHasher) -> None:
        self._uow = uow
        self._password_hasher = password_hasher

    async def execute(self, command: RegisterUserCommand) -> UserResult:
        async with self._uow as uow:
            existing = await uow.users.get_by_username(command.username)
            if existing is not None:
                raise UsernameAlreadyExistsError(command.username)

            user = User(
                username=command.username,
                email=command.email,
                hashed_password=self._password_hasher.hash(command.password),
                role=command.role,
            )
            await uow.users.add(user)
            await uow.commit()
            return user_to_result(user)
