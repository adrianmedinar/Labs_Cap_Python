"""Puerto (interfaz): UnitOfWork.

Patrón Unit of Work: agrupa operaciones sobre uno o más repositorios en una
sola transacción atómica. Los casos de uso reciben una fábrica/instancia de
este puerto y la usan como *context manager* para garantizar
commit/rollback consistente, sin conocer si por debajo hay SQLAlchemy,
Mongo u otra tecnología.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from purchase_orders.domain.ports.purchase_order_repository import (
    PurchaseOrderRepository,
)
from purchase_orders.domain.ports.supplier_repository import SupplierRepository
from purchase_orders.domain.ports.user_repository import UserRepository


class UnitOfWork(ABC):
    purchase_orders: PurchaseOrderRepository
    suppliers: SupplierRepository
    users: UserRepository

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
