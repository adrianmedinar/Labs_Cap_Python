"""Adaptador: SqlAlchemyUnitOfWork.

Implementa el puerto `UnitOfWork` sobre una `AsyncSession` de SQLAlchemy.
Cada caso de uso obtiene una instancia nueva (vía factory) por request/
operación, garantizando aislamiento transaccional.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from purchase_orders.domain.ports.unit_of_work import UnitOfWork
from purchase_orders.infrastructure.db.repositories.purchase_order_repository import (
    SqlAlchemyPurchaseOrderRepository,
)
from purchase_orders.infrastructure.db.repositories.supplier_repository import (
    SqlAlchemySupplierRepository,
)
from purchase_orders.infrastructure.db.repositories.user_repository import (
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.purchase_orders = SqlAlchemyPurchaseOrderRepository(self._session)
        self.suppliers = SqlAlchemySupplierRepository(self._session)
        self.users = SqlAlchemyUserRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
