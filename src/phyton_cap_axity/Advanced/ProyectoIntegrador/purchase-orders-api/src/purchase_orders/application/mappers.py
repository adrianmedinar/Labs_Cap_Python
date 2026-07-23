"""Mappers: conversión entre entidades de dominio y DTOs de aplicación.

Mantener esta lógica centralizada evita duplicar la conversión en cada
caso de uso y evita que las entidades de dominio necesiten saber cómo
serializarse (eso sería una fuga de responsabilidad de infraestructura
hacia el dominio).
"""

from __future__ import annotations

from purchase_orders.application.dtos.common_dto import SupplierResult, UserResult
from purchase_orders.application.dtos.purchase_order_dto import (
    LineItemResult,
    PurchaseOrderResult,
)
from purchase_orders.domain.entities.purchase_order import PurchaseOrder
from purchase_orders.domain.entities.supplier import Supplier
from purchase_orders.domain.entities.user import User


def purchase_order_to_result(order: PurchaseOrder) -> PurchaseOrderResult:
    return PurchaseOrderResult(
        id=order.id,
        supplier_id=order.supplier_id,
        status=order.status.value,
        currency=order.currency,
        requested_by=order.requested_by,
        approved_by=order.approved_by,
        rejection_reason=order.rejection_reason,
        line_items=[
            LineItemResult(
                sku=li.sku,
                description=li.description,
                quantity=li.quantity,
                unit_price=str(li.unit_price.amount),
                subtotal=str(li.subtotal.amount),
            )
            for li in order.line_items
        ],
        total=str(order.total.amount),
        created_at=order.created_at,
        updated_at=order.updated_at,
        version=order.version,
    )


def supplier_to_result(supplier: Supplier) -> SupplierResult:
    return SupplierResult(
        id=supplier.id,
        name=supplier.name,
        tax_id=supplier.tax_id,
        email=supplier.email,
        is_active=supplier.is_active,
    )


def user_to_result(user: User) -> UserResult:
    return UserResult(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )
