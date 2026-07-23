"""Caso de uso: Rechazar Orden de Compra."""

from __future__ import annotations

from purchase_orders.application.dtos.purchase_order_dto import (
    PurchaseOrderResult,
    RejectPurchaseOrderCommand,
)
from purchase_orders.application.exceptions import ResourceNotFoundError
from purchase_orders.application.mappers import purchase_order_to_result
from purchase_orders.domain.ports.unit_of_work import UnitOfWork


class RejectPurchaseOrderUseCase:
    """Transiciona una orden de PENDING_APPROVAL a REJECTED."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RejectPurchaseOrderCommand) -> PurchaseOrderResult:
        async with self._uow as uow:
            order = await uow.purchase_orders.get_by_id(command.order_id)
            if order is None:
                raise ResourceNotFoundError("PurchaseOrder", command.order_id)

            order.reject(reason=command.reason)

            await uow.purchase_orders.update(order)
            await uow.commit()
            return purchase_order_to_result(order)
