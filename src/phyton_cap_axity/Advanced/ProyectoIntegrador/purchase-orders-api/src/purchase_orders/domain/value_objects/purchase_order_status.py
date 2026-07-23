"""Value Object: PurchaseOrderStatus.

Define el ciclo de vida (máquina de estados) de una Orden de Compra y las
transiciones válidas entre estados. Esta es una regla de negocio central:
ninguna orden puede saltarse estados o retroceder de forma inválida.

Transiciones permitidas:

    DRAFT --submit--> PENDING_APPROVAL
    PENDING_APPROVAL --approve--> APPROVED
    PENDING_APPROVAL --reject--> REJECTED
    APPROVED --send--> SENT_TO_SUPPLIER
    SENT_TO_SUPPLIER --confirm_receipt--> RECEIVED
    RECEIVED --close--> CLOSED
    {DRAFT, PENDING_APPROVAL, APPROVED} --cancel--> CANCELLED
"""

from __future__ import annotations

from enum import Enum


class PurchaseOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENT_TO_SUPPLIER = "SENT_TO_SUPPLIER"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


# Mapa de transiciones válidas: acción -> {estado_actual -> estado_destino}
_TRANSITIONS: dict[str, dict[PurchaseOrderStatus, PurchaseOrderStatus]] = {
    "submit": {PurchaseOrderStatus.DRAFT: PurchaseOrderStatus.PENDING_APPROVAL},
    "approve": {PurchaseOrderStatus.PENDING_APPROVAL: PurchaseOrderStatus.APPROVED},
    "reject": {PurchaseOrderStatus.PENDING_APPROVAL: PurchaseOrderStatus.REJECTED},
    "send": {PurchaseOrderStatus.APPROVED: PurchaseOrderStatus.SENT_TO_SUPPLIER},
    "confirm_receipt": {
        PurchaseOrderStatus.SENT_TO_SUPPLIER: PurchaseOrderStatus.RECEIVED
    },
    "close": {PurchaseOrderStatus.RECEIVED: PurchaseOrderStatus.CLOSED},
    "cancel": {
        PurchaseOrderStatus.DRAFT: PurchaseOrderStatus.CANCELLED,
        PurchaseOrderStatus.PENDING_APPROVAL: PurchaseOrderStatus.CANCELLED,
        PurchaseOrderStatus.APPROVED: PurchaseOrderStatus.CANCELLED,
    },
}


def can_transition(current: PurchaseOrderStatus, action: str) -> bool:
    return current in _TRANSITIONS.get(action, {})


def next_state(current: PurchaseOrderStatus, action: str) -> PurchaseOrderStatus:
    return _TRANSITIONS[action][current]


def is_terminal(status: PurchaseOrderStatus) -> bool:
    return status in {
        PurchaseOrderStatus.REJECTED,
        PurchaseOrderStatus.CLOSED,
        PurchaseOrderStatus.CANCELLED,
    }
