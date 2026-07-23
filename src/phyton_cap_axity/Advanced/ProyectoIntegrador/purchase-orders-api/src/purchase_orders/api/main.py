"""Punto de entrada de la API:

Ensambla el `Container` de infraestructura, registra routers, manejadores
de excepciones, CORS y metadata de OpenAPI. Se expone `create_app()`
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from purchase_orders.api.error_handlers import register_exception_handlers
from purchase_orders.api.routers import (
    auth_router,
    purchase_order_router,
    supplier_router,
)
from purchase_orders.infrastructure.config import Settings, get_settings
from purchase_orders.infrastructure.container import Container

_DESCRIPTION = """
API REST para la gestión del ciclo de vida completo de **Órdenes de
Compra**, construida con **arquitectura hexagonal**
(dominio / aplicación / infraestructura / API).

### Ciclo de vida de una orden

```
DRAFT --submit--> PENDING_APPROVAL --approve--> APPROVED
                                                    |
                                          send-to-supplier
                                                    v
                                          SENT_TO_SUPPLIER
                        |                            |
                     reject                       cancel
                        v                            v
                    REJECTED                     CANCELLED

SENT_TO_SUPPLIER --confirm-receipt--> RECEIVED --close--> CLOSED
```

### Autenticación

1. Registra un usuario en `POST /api/v1/auth/register`.
2. Obtén un token en `POST /api/v1/auth/login` (compatible con el botón
   **Authorize** de esta página).
3. Usa el token como `Authorization: Bearer <token>` en el resto de endpoints.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Startup: se ensambla el contenedor de dependencias una sola vez
        # por proceso y se cuelga de `app.state` para que las dependencias
        # de FastAPI puedan recuperarlo por request.
        app.state.container = Container(settings)
        yield
        # Shutdown: liberar el pool de conexiones del engine.
        await app.state.container.dispose()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=_DESCRIPTION,
        lifespan=lifespan,
        contact={"name": "Adrian M."},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(auth_router.router)
    app.include_router(supplier_router.router)
    app.include_router(purchase_order_router.router)

    @app.get("/health", tags=["Salud"], summary="Health check")
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


# Instancia usada por `uvicorn purchase_orders.api.main:app`
app = create_app()
