"""Caso de uso: Crear Orden de Compra."""

from __future__ import annotations

from purchase_orders.application.dtos.purchase_order_dto import (
    CreatePurchaseOrderCommand,
    PurchaseOrderResult,
)
from purchase_orders.application.exceptions import ResourceNotFoundError
from purchase_orders.application.mappers import purchase_order_to_result
from purchase_orders.domain.entities.purchase_order import PurchaseOrder
from purchase_orders.domain.ports.unit_of_work import UnitOfWork
from purchase_orders.domain.value_objects.line_item import LineItem
from purchase_orders.domain.value_objects.money import Money


class CreatePurchaseOrderUseCase:
    """Orquesta la creación de una orden de compra en estado DRAFT."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreatePurchaseOrderCommand) -> PurchaseOrderResult:
        async with self._uow as uow:
            supplier = await uow.suppliers.get_by_id(command.supplier_id)
            if supplier is None:
                raise ResourceNotFoundError("Supplier", command.supplier_id)

            line_items = [
                LineItem(
                    sku=item.sku,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=Money.from_str(item.unit_price, command.currency),
                )
                for item in command.line_items
            ]

            order = PurchaseOrder.create(
                supplier_id=command.supplier_id,
                requested_by=command.requested_by,
                line_items=line_items,
                currency=command.currency,
            )

            await uow.purchase_orders.add(order)
            await uow.commit()
            return purchase_order_to_result(order)
