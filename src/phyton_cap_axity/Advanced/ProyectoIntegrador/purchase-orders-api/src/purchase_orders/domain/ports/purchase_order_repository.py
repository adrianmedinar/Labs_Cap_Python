"""Puerto (interfaz): PurchaseOrderRepository.

Contrato que debe cumplir cualquier adaptador de persistencia para
Órdenes de Compra (SQLAlchemy, memoria, Mongo, etc). El dominio y la
aplicación dependen únicamente de esta abstracción, nunca de una
implementación concreta (Dependency Inversion Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from purchase_orders.domain.entities.purchase_order import PurchaseOrder


class PurchaseOrderRepository(ABC):
    @abstractmethod
    async def add(self, order: PurchaseOrder) -> None:
        """Persiste una nueva orden de compra."""

    @abstractmethod
    async def get_by_id(self, order_id: UUID) -> PurchaseOrder | None:
        """Recupera una orden por su identificador. `None` si no existe."""

    @abstractmethod
    async def update(self, order: PurchaseOrder) -> None:
        """Persiste cambios sobre una orden existente (optimistic locking)."""

    @abstractmethod
    async def list_by_status(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[PurchaseOrder]:
        """Lista órdenes, opcionalmente filtradas por estado, con paginación."""

    @abstractmethod
    async def list_by_supplier(
        self, supplier_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[PurchaseOrder]:
        """Lista órdenes de un proveedor específico, con paginación."""
