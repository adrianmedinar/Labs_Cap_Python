"""DTOs de la capa de aplicación para Órdenes de Compra.

Estos objetos son el "lenguaje" con el que la capa de aplicación se
comunica hacia afuera (API) y hacia adentro (dominio). Son simples
`dataclasses`, deliberadamente sin dependencia de Pydantic ni de FastAPI:
así la capa de aplicación permanece independiente de frameworks web y
puede reutilizarse desde una CLI, un worker, o cualquier otro adaptador
de entrada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LineItemCommand:
    sku: str
    description: str
    quantity: int
    unit_price: str  # se recibe como string para preservar precisión decimal


@dataclass(frozen=True, slots=True)
class CreatePurchaseOrderCommand:
    supplier_id: UUID
    requested_by: str
    line_items: list[LineItemCommand]
    currency: str = "MXN"


@dataclass(frozen=True, slots=True)
class ApprovePurchaseOrderCommand:
    order_id: UUID
    approved_by: str
    approver_role: str


@dataclass(frozen=True, slots=True)
class RejectPurchaseOrderCommand:
    order_id: UUID
    reason: str


@dataclass(frozen=True, slots=True)
class LineItemResult:
    sku: str
    description: str
    quantity: int
    unit_price: str
    subtotal: str


@dataclass(frozen=True, slots=True)
class PurchaseOrderResult:
    """Representación de solo lectura de una orden, para devolver al exterior."""

    id: UUID
    supplier_id: UUID
    status: str
    currency: str
    requested_by: str
    approved_by: str | None
    rejection_reason: str | None
    line_items: list[LineItemResult]
    total: str
    created_at: datetime
    updated_at: datetime
    version: int
