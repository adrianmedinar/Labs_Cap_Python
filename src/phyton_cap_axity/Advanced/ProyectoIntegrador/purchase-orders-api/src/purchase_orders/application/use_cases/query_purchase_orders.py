"""Casos de uso de consulta (queries) para Órdenes de Compra.

Se agrupan porque son operaciones de solo lectura sin efectos secundarios
de negocio; separarlas de los comandos (que sí mutan estado) es una
práctica CQRS ligera que clarifica cuáles casos de uso requieren
commit/transacción y cuáles no.
"""

from __future__ import annotations

from uuid import UUID

from purchase_orders.application.dtos.purchase_order_dto import PurchaseOrderResult
from purchase_orders.application.exceptions import ResourceNotFoundError
from purchase_orders.application.mappers import purchase_order_to_result
from purchase_orders.domain.ports.unit_of_work import UnitOfWork


class GetPurchaseOrderUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, order_id: UUID) -> PurchaseOrderResult:
        async with self._uow as uow:
            order = await uow.purchase_orders.get_by_id(order_id)
            if order is None:
                raise ResourceNotFoundError("PurchaseOrder", order_id)
            return purchase_order_to_result(order)


class ListPurchaseOrdersUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        status: str | None = None,
        supplier_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PurchaseOrderResult]:
        async with self._uow as uow:
            if supplier_id is not None:
                orders = await uow.purchase_orders.list_by_supplier(
                    supplier_id, limit=limit, offset=offset
                )
            else:
                orders = await uow.purchase_orders.list_by_status(
                    status, limit=limit, offset=offset
                )
            return [purchase_order_to_result(o) for o in orders]
