"""Manejadores de excepciones: traducen errores de dominio/aplicación a
respuestas HTTP con códigos de estado semánticamente correctos.

Esta es la frontera donde las excepciones "puras" del negocio (que no
saben nada de HTTP) se convierten en respuestas JSON estándar. Mantiene
el dominio y la aplicación completamente libres de conocimiento HTTP.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from purchase_orders.application.exceptions import (
    ApplicationError,
    InvalidCredentialsError,
    ResourceNotFoundError,
    UsernameAlreadyExistsError,
)
from purchase_orders.domain.exceptions.domain_exceptions import (
    ApprovalThresholdExceededError,
    CurrencyMismatchError,
    DomainError,
    EmptyPurchaseOrderError,
    InvalidLineItemQuantityError,
    InvalidMoneyAmountError,
    InvalidPurchaseOrderStateError,
    PurchaseOrderNotFoundError,
    SupplierNotFoundError,
    UnauthorizedActionError,
)
from purchase_orders.infrastructure.db.repositories.purchase_order_repository import (
    ConcurrentModificationError,
)
from purchase_orders.infrastructure.security.jwt_token_provider import (
    InvalidTokenException,
)

# Mapa explícito excepción -> status HTTP. Usar un mapa (en vez de
# encadenar isinstance) hace evidente, de un vistazo, la política de
# traducción completa del sistema.
_STATUS_MAP: dict[type[Exception], int] = {
    # 400 Bad Request: entrada inválida / violación de invariante simple
    EmptyPurchaseOrderError: status.HTTP_400_BAD_REQUEST,
    InvalidLineItemQuantityError: status.HTTP_400_BAD_REQUEST,
    InvalidMoneyAmountError: status.HTTP_400_BAD_REQUEST,
    CurrencyMismatchError: status.HTTP_400_BAD_REQUEST,
    # 401 Unauthorized: credenciales o token inválidos
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenException: status.HTTP_401_UNAUTHORIZED,
    # 403 Forbidden: autenticado pero sin permiso para la acción
    UnauthorizedActionError: status.HTTP_403_FORBIDDEN,
    ApprovalThresholdExceededError: status.HTTP_403_FORBIDDEN,
    # 404 Not Found
    ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    PurchaseOrderNotFoundError: status.HTTP_404_NOT_FOUND,
    SupplierNotFoundError: status.HTTP_404_NOT_FOUND,
    # 409 Conflict: estado/concurrencia
    InvalidPurchaseOrderStateError: status.HTTP_409_CONFLICT,
    UsernameAlreadyExistsError: status.HTTP_409_CONFLICT,
    ConcurrentModificationError: status.HTTP_409_CONFLICT,
}


def _resolve_status_code(exc: Exception) -> int:
    for exc_type, status_code in _STATUS_MAP.items():
        if isinstance(exc, exc_type):
            return status_code
    # Fallback conservador para cualquier DomainError/ApplicationError
    # no mapeada explícitamente.
    if isinstance(exc, DomainError | ApplicationError):
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def _handle_business_exception(request: Request, exc: Exception) -> JSONResponse:
    status_code = _resolve_status_code(exc)
    headers = (
        {"WWW-Authenticate": "Bearer"}
        if status_code == status.HTTP_401_UNAUTHORIZED
        else None
    )
    return JSONResponse(
        status_code=status_code, content={"detail": str(exc)}, headers=headers
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores de excepciones de negocio en la app."""
    app.add_exception_handler(DomainError, _handle_business_exception)
    app.add_exception_handler(ApplicationError, _handle_business_exception)
    app.add_exception_handler(ConcurrentModificationError, _handle_business_exception)
    app.add_exception_handler(InvalidTokenException, _handle_business_exception)
