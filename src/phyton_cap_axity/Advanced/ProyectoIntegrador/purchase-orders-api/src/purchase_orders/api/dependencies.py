"""Dependencias de FastAPI: inyección de contenedor, UnitOfWork, y
autenticación/autorización basada en JWT.

Estas dependencias son el ÚNICO punto donde la API traduce el esquema
OAuth2/JWT hacia los puertos del dominio (`TokenProvider`) y los casos de
uso de aplicación.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from purchase_orders.domain.ports.token_provider import TokenPayload
from purchase_orders.domain.ports.unit_of_work import UnitOfWork
from purchase_orders.infrastructure.container import Container
from purchase_orders.infrastructure.security.jwt_token_provider import (
    InvalidTokenException,
)

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_container(request: Request) -> Container:
    """Recupera el contenedor de dependencias almacenado en `app.state`."""
    return request.app.state.container  # type: ignore[no-any-return]


def get_unit_of_work(
    container: Annotated[Container, Depends(get_container)],
) -> UnitOfWork:
    """Provee una instancia nueva de UnitOfWork por request."""
    return container.unit_of_work()


def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    container: Annotated[Container, Depends(get_container)],
) -> TokenPayload:
    """Decodifica el JWT del header `Authorization: Bearer <token>` y
    devuelve el payload autenticado. Lanza 401 si el token es inválido.
    """
    try:
        return container.token_provider.decode(token)
    except InvalidTokenException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ContainerDep = Annotated[Container, Depends(get_container)]


def require_roles(*allowed_roles: str) -> Callable[[CurrentUser], TokenPayload]:
    """Fábrica de dependencia: exige que el usuario autenticado tenga uno
    de los roles permitidos. Uso: `Depends(require_roles("admin"))`.
    """

    def _dependency(current_user: CurrentUser) -> TokenPayload:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"El rol '{current_user.role}' no tiene permiso para "
                    f"esta operación. Roles permitidos: {', '.join(allowed_roles)}."
                ),
            )
        return current_user

    return _dependency
