"""Router: Autenticación (registro de usuarios y login con JWT)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from purchase_orders.api.dependencies import ContainerDep, UnitOfWorkDep
from purchase_orders.api.schemas.auth_schemas import (
    RegisterUserRequest,
    TokenResponse,
    UserResponse,
)
from purchase_orders.api.schemas.error_schemas import ErrorResponse
from purchase_orders.application.dtos.common_dto import (
    LoginCommand,
    RegisterUserCommand,
)
from purchase_orders.application.use_cases.login import LoginUseCase
from purchase_orders.application.use_cases.register_user import RegisterUserUseCase

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    responses={409: {"model": ErrorResponse, "description": "Usuario ya existe"}},
)
async def register(
    payload: RegisterUserRequest,
    uow: UnitOfWorkDep,
    container: ContainerDep,
) -> UserResponse:
    use_case = RegisterUserUseCase(uow, container.password_hasher)
    result = await use_case.execute(
        RegisterUserCommand(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            role=payload.role,
        )
    )
    return UserResponse.model_validate(result, from_attributes=True)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión y obtener un token JWT",
    description=(
        "Compatible con el flujo estándar OAuth2 Password Flow, por lo que "
        "funciona directamente con el botón 'Authorize' de esta documentación."
    ),
    responses={401: {"model": ErrorResponse, "description": "Credenciales inválidas"}},
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: UnitOfWorkDep,
    container: ContainerDep,
) -> TokenResponse:
    use_case = LoginUseCase(uow, container.password_hasher, container.token_provider)
    result = await use_case.execute(
        LoginCommand(username=form_data.username, password=form_data.password)
    )
    return TokenResponse(access_token=result.access_token, token_type=result.token_type)
