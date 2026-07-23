"""Contenedor de dependencias (composition root).

Este es el ÚNICO lugar del proyecto donde se instancian adaptadores
concretos de infraestructura y se "conectan" a los puertos del dominio.
El resto del código (dominio, aplicación, API) solo conoce interfaces.

Vive en `infrastructure` porque, precisamente, es responsabilidad de la
infraestructura decidir qué implementación concreta usar para cada puerto.
"""

from __future__ import annotations

from purchase_orders.infrastructure.config import Settings
from purchase_orders.infrastructure.db.base import (
    create_engine,
    create_session_factory,
)
from purchase_orders.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from purchase_orders.infrastructure.security.jwt_token_provider import (
    JwtTokenProvider,
)
from purchase_orders.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)


class Container:
    """Composition root: crea y expone los adaptadores singleton del proceso."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_engine(settings.database_url, echo=settings.database_echo)
        self.session_factory = create_session_factory(self.engine)
        self.password_hasher = BcryptPasswordHasher()
        self.token_provider = JwtTokenProvider(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_access_token_expire_minutes,
        )

    def unit_of_work(self) -> SqlAlchemyUnitOfWork:
        """Crea una nueva instancia de UnitOfWork por operación/request."""
        return SqlAlchemyUnitOfWork(self.session_factory)

    async def dispose(self) -> None:
        await self.engine.dispose()
