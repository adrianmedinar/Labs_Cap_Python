"""Casos de uso: transiciones finales del ciclo de vida de la Orden de Compra.

Se agrupan en un solo módulo (SendToSupplier, ConfirmReceipt, Close, Cancel)
porque comparten exactamente la misma forma: cargar la orden, invocar una
transición sin parámetros adicionales de negocio, persistir y mapear el
resultado. Mantenerlos juntos evita repetir cuatro archivos casi idénticos
sin sacrificar claridad (cada uno sigue siendo una clase independiente y
con una única responsabilidad).
"""

from __future__ import annotations

from uuid import UUID

from purchase_orders.application.dtos.purchase_order_dto import PurchaseOrderResult
from purchase_orders.application.exceptions import ResourceNotFoundError
from purchase_orders.application.mappers import purchase_order_to_result
from purchase_orders.domain.entities.purchase_order import PurchaseOrder
from purchase_orders.domain.ports.unit_of_work import UnitOfWork


class _BasePurchaseOrderTransitionUseCase:
    """Clase base interna: no expuesta como caso de uso por sí misma."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def _apply_transition(self, order: PurchaseOrder) -> None:
        raise NotImplementedError

    async def execute(self, order_id: UUID) -> PurchaseOrderResult:
        async with self._uow as uow:
            order = await uow.purchase_orders.get_by_id(order_id)
            if order is None:
                raise ResourceNotFoundError("PurchaseOrder", order_id)

            self._apply_transition(order)

            await uow.purchase_orders.update(order)
            await uow.commit()
            return purchase_order_to_result(order)


class SendToSupplierUseCase(_BasePurchaseOrderTransitionUseCase):
    """Transiciona una orden de APPROVED a SENT_TO_SUPPLIER."""

    def _apply_transition(self, order: PurchaseOrder) -> None:
        order.send_to_supplier()


class ConfirmReceiptUseCase(_BasePurchaseOrderTransitionUseCase):
    """Transiciona una orden de SENT_TO_SUPPLIER a RECEIVED."""

    def _apply_transition(self, order: PurchaseOrder) -> None:
        order.confirm_receipt()


class ClosePurchaseOrderUseCase(_BasePurchaseOrderTransitionUseCase):
    """Transiciona una orden de RECEIVED a CLOSED."""

    def _apply_transition(self, order: PurchaseOrder) -> None:
        order.close()


class CancelPurchaseOrderUseCase(_BasePurchaseOrderTransitionUseCase):
    """Cancela una orden desde DRAFT, PENDING_APPROVAL o APPROVED."""

    def _apply_transition(self, order: PurchaseOrder) -> None:
        order.cancel()
