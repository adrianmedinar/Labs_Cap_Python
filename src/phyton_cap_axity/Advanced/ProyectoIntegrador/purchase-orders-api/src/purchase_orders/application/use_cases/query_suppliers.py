"""Casos de uso de consulta para Proveedores."""

from __future__ import annotations

from uuid import UUID

from purchase_orders.application.dtos.common_dto import SupplierResult
from purchase_orders.application.exceptions import ResourceNotFoundError
from purchase_orders.application.mappers import supplier_to_result
from purchase_orders.domain.ports.unit_of_work import UnitOfWork


class GetSupplierUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, supplier_id: UUID) -> SupplierResult:
        async with self._uow as uow:
            supplier = await uow.suppliers.get_by_id(supplier_id)
            if supplier is None:
                raise ResourceNotFoundError("Supplier", supplier_id)
            return supplier_to_result(supplier)


class ListSuppliersUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, limit: int = 50, offset: int = 0) -> list[SupplierResult]:
        async with self._uow as uow:
            suppliers = await uow.suppliers.list_active(limit=limit, offset=offset)
            return [supplier_to_result(s) for s in suppliers]
