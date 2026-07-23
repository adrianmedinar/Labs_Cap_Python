"""Puerto (interfaz): SupplierRepository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from purchase_orders.domain.entities.supplier import Supplier


class SupplierRepository(ABC):
    @abstractmethod
    async def add(self, supplier: Supplier) -> None:
        """Persiste un nuevo proveedor."""

    @abstractmethod
    async def get_by_id(self, supplier_id: UUID) -> Supplier | None:
        """Recupera un proveedor por su identificador."""

    @abstractmethod
    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Supplier]:
        """Lista proveedores activos, con paginación."""
