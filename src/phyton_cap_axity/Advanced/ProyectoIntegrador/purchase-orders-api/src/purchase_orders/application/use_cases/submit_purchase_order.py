"""Caso de uso: Enviar Orden de Compra a aprobación (submit)."""

from __future__ import annotations

from uuid import UUID

from purchase_orders.application.dtos.purchase_order_dto import PurchaseOrderResult
from purchase_orders.application.exceptions import ResourceNotFoundError
from purchase_orders.application.mappers import purchase_order_to_result
from purchase_orders.domain.ports.unit_of_work import UnitOfWork


class SubmitPurchaseOrderUseCase:
    """Transiciona una orden de DRAFT a PENDING_APPROVAL."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, order_id: UUID) -> PurchaseOrderResult:
        async with self._uow as uow:
            order = await uow.purchase_orders.get_by_id(order_id)
            if order is None:
                raise ResourceNotFoundError("PurchaseOrder", order_id)

            order.submit()

            await uow.purchase_orders.update(order)
            await uow.commit()
            return purchase_order_to_result(order)
