"""Pruebas unitarias: casos de uso de Autenticación (registro y login)."""

from __future__ import annotations

import pytest

from purchase_orders.application.dtos.common_dto import (
    LoginCommand,
    RegisterUserCommand,
)
from purchase_orders.application.exceptions import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
)
from purchase_orders.application.use_cases.login import LoginUseCase
from purchase_orders.application.use_cases.register_user import RegisterUserUseCase
from tests.support.fakes import FakePasswordHasher, FakeTokenProvider, FakeUnitOfWork

pytestmark = pytest.mark.unit


def _register_command(**overrides) -> RegisterUserCommand:
    defaults: dict = {
        "username": "jane",
        "email": "jane@corp.com",
        "password": "secret123",
        "role": "approver_senior",
    }
    defaults.update(overrides)
    return RegisterUserCommand(**defaults)


class TestRegisterUserUseCase:
    async def test_registra_usuario_con_password_hasheado(self) -> None:
        uow = FakeUnitOfWork()
        hasher = FakePasswordHasher()

        result = await RegisterUserUseCase(uow, hasher).execute(_register_command())

        stored = await uow.users.get_by_username("jane")
        assert stored is not None
        assert stored.hashed_password != "secret123"
        assert result.username == "jane"
        assert result.role == "approver_senior"

    async def test_rechaza_username_duplicado(self) -> None:
        uow = FakeUnitOfWork()
        hasher = FakePasswordHasher()
        await RegisterUserUseCase(uow, hasher).execute(_register_command())

        with pytest.raises(UsernameAlreadyExistsError):
            await RegisterUserUseCase(uow, hasher).execute(_register_command())


class TestLoginUseCase:
    async def test_login_exitoso_retorna_token(self) -> None:
        uow = FakeUnitOfWork()
        hasher = FakePasswordHasher()
        token_provider = FakeTokenProvider()
        await RegisterUserUseCase(uow, hasher).execute(_register_command())

        result = await LoginUseCase(uow, hasher, token_provider).execute(
            LoginCommand(username="jane", password="secret123")
        )

        assert result.token_type == "bearer"
        assert "jane" in result.access_token

    async def test_login_rechaza_password_incorrecto(self) -> None:
        uow = FakeUnitOfWork()
        hasher = FakePasswordHasher()
        token_provider = FakeTokenProvider()
        await RegisterUserUseCase(uow, hasher).execute(_register_command())

        with pytest.raises(InvalidCredentialsError):
            await LoginUseCase(uow, hasher, token_provider).execute(
                LoginCommand(username="jane", password="wrong-password")
            )

    async def test_login_rechaza_usuario_inexistente(self) -> None:
        uow = FakeUnitOfWork()
        hasher = FakePasswordHasher()
        token_provider = FakeTokenProvider()

        with pytest.raises(InvalidCredentialsError):
            await LoginUseCase(uow, hasher, token_provider).execute(
                LoginCommand(username="ghost", password="whatever")
            )
