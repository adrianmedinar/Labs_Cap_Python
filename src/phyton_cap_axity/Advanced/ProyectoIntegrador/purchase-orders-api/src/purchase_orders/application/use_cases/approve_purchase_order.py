"""Caso de uso: Aprobar Orden de Compra."""

from __future__ import annotations

from purchase_orders.application.dtos.purchase_order_dto import (
    ApprovePurchaseOrderCommand,
    PurchaseOrderResult,
)
from purchase_orders.application.exceptions import ResourceNotFoundError
from purchase_orders.application.mappers import purchase_order_to_result
from purchase_orders.domain.ports.unit_of_work import UnitOfWork
from purchase_orders.domain.services.approval_policy import ApprovalPolicy


class ApprovePurchaseOrderUseCase:
    """Transiciona una orden de PENDING_APPROVAL a APPROVED, validando el
    límite de aprobación del rol del aprobador (regla de negocio delegada
    al servicio de dominio `ApprovalPolicy`).
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, command: ApprovePurchaseOrderCommand
    ) -> PurchaseOrderResult:
        async with self._uow as uow:
            order = await uow.purchase_orders.get_by_id(command.order_id)
            if order is None:
                raise ResourceNotFoundError("PurchaseOrder", command.order_id)

            max_amount = ApprovalPolicy.max_approvable_amount(
                command.approver_role, order.currency
            )
            order.approve(
                approved_by=command.approved_by, approver_max_amount=max_amount
            )

            await uow.purchase_orders.update(order)
            await uow.commit()
            return purchase_order_to_result(order)
