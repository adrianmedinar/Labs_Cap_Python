"""Servicio de dominio: política de aprobación de Órdenes de Compra.

Encapsula la regla de negocio "cuánto puede aprobar cada rol", que no
pertenece naturalmente a `PurchaseOrder` ni a `Supplier` (cruza el concepto
de rol/usuario, que vive en el contexto de identidad). Vive como *domain
service* porque coordina una decisión de negocio sin ser responsabilidad
única de una entidad.
"""

from __future__ import annotations

from purchase_orders.domain.exceptions.domain_exceptions import (
    UnauthorizedActionError,
)
from purchase_orders.domain.value_objects.money import Money

# Límite máximo de aprobación por rol. En un sistema real esto podría
# provenir de un puerto de configuración; aquí se modela como política
# explícita del dominio para mantener el ejemplo autocontenido.
_APPROVAL_LIMITS: dict[str, Money] = {
    "approver_junior": Money.from_str("5000.00"),
    "approver_senior": Money.from_str("50000.00"),
    "admin": Money.from_str("1000000.00"),
}

_ROLES_ALLOWED_TO_APPROVE = frozenset(_APPROVAL_LIMITS.keys())


class ApprovalPolicy:
    """Determina si un rol puede aprobar y cuál es su límite autorizable."""

    @staticmethod
    def max_approvable_amount(role: str, currency: str = "MXN") -> Money:
        if role not in _ROLES_ALLOWED_TO_APPROVE:
            raise UnauthorizedActionError(action="approve_purchase_order", role=role)
        limit = _APPROVAL_LIMITS[role]
        return Money(limit.amount, currency)

    @staticmethod
    def can_approve(role: str) -> bool:
        return role in _ROLES_ALLOWED_TO_APPROVE
