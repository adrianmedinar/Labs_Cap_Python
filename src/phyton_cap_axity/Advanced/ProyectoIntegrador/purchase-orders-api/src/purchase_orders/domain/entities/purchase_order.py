"""Entidad raíz del agregado: PurchaseOrder (Orden de Compra).

Esta clase concentra TODA la lógica de negocio del ciclo de vida de una
orden de compra. Los casos de uso (capa de aplicación) nunca manipulan
el estado directamente: siempre invocan métodos de este agregado, que
garantizan invariantes de negocio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from purchase_orders.domain.exceptions.domain_exceptions import (
    ApprovalThresholdExceededError,
    EmptyPurchaseOrderError,
    InvalidPurchaseOrderStateError,
)
from purchase_orders.domain.value_objects.line_item import LineItem
from purchase_orders.domain.value_objects.money import Money
from purchase_orders.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
    can_transition,
    next_state,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class PurchaseOrder:
    """Agregado raíz. Identidad = `id`. El resto es mutable solo vía métodos."""

    supplier_id: UUID
    currency: str
    id: UUID = field(default_factory=uuid4)
    line_items: list[LineItem] = field(default_factory=list)
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    requested_by: str = ""
    approved_by: str | None = None
    rejection_reason: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    version: int = 1  # para control de concurrencia optimista

    # ---------------------------------------------------------------
    # Construcción
    # ---------------------------------------------------------------
    @classmethod
    def create(
        cls,
        supplier_id: UUID,
        requested_by: str,
        line_items: list[LineItem],
        currency: str = "MXN",
    ) -> PurchaseOrder:
        if not line_items:
            raise EmptyPurchaseOrderError()
        return cls(
            supplier_id=supplier_id,
            currency=currency,
            line_items=list(line_items),
            requested_by=requested_by,
        )

    # ---------------------------------------------------------------
    # Consultas derivadas
    # ---------------------------------------------------------------
    @property
    def total(self) -> Money:
        total = Money.zero(self.currency)
        for item in self.line_items:
            total = total + item.subtotal
        return total

    # ---------------------------------------------------------------
    # Comportamiento de negocio (transiciones de estado)
    # ---------------------------------------------------------------
    def add_line_item(self, item: LineItem) -> None:
        self._ensure_editable("add_line_item")
        self.line_items.append(item)
        self._touch()

    def remove_line_item(self, sku: str) -> None:
        self._ensure_editable("remove_line_item")
        self.line_items = [li for li in self.line_items if li.sku != sku]
        if not self.line_items:
            raise EmptyPurchaseOrderError()
        self._touch()

    def submit(self) -> None:
        if not self.line_items:
            raise EmptyPurchaseOrderError()
        self._transition("submit")

    def approve(self, approved_by: str, approver_max_amount: Money) -> None:
        if self.total > approver_max_amount:
            raise ApprovalThresholdExceededError(self.total, approver_max_amount)
        self._transition("approve")
        self.approved_by = approved_by

    def reject(self, reason: str) -> None:
        self._transition("reject")
        self.rejection_reason = reason

    def send_to_supplier(self) -> None:
        self._transition("send")

    def confirm_receipt(self) -> None:
        self._transition("confirm_receipt")

    def close(self) -> None:
        self._transition("close")

    def cancel(self) -> None:
        self._transition("cancel")

    # ---------------------------------------------------------------
    # Internos
    # ---------------------------------------------------------------
    def _ensure_editable(self, action: str) -> None:
        if self.status != PurchaseOrderStatus.DRAFT:
            raise InvalidPurchaseOrderStateError(self.status.value, action)

    def _transition(self, action: str) -> None:
        if not can_transition(self.status, action):
            raise InvalidPurchaseOrderStateError(self.status.value, action)
        self.status = next_state(self.status, action)
        self._touch()

    def _touch(self) -> None:
        self.updated_at = _utcnow()
        self.version += 1
