"""Excepciones del dominio de Órdenes de Compra.

Estas excepciones representan violaciones de reglas de negocio y son
independientes de cualquier framework o mecanismo de transporte (HTTP, etc).
La capa de API se encarga de traducirlas a códigos de estado apropiados.
"""

from __future__ import annotations


class DomainError(Exception):
    """Excepción base para todos los errores de dominio."""


class InvalidPurchaseOrderStateError(DomainError):
    """Se intentó una transición de estado no permitida en una orden de compra."""

    def __init__(self, current_state: str, attempted_action: str) -> None:
        self.current_state = current_state
        self.attempted_action = attempted_action
        super().__init__(
            f"No se puede ejecutar '{attempted_action}' estando en estado "
            f"'{current_state}'."
        )


class EmptyPurchaseOrderError(DomainError):
    """Una orden de compra no puede existir sin al menos una línea de ítem."""

    def __init__(self) -> None:
        super().__init__("La orden de compra debe contener al menos un ítem.")


class InvalidLineItemQuantityError(DomainError):
    """La cantidad de un ítem debe ser un entero positivo."""

    def __init__(self, quantity: int) -> None:
        self.quantity = quantity
        super().__init__(f"La cantidad debe ser mayor a cero, se recibió: {quantity}.")


class InvalidMoneyAmountError(DomainError):
    """Un monto monetario no puede ser negativo."""

    def __init__(self, amount: object) -> None:
        self.amount = amount
        super().__init__(f"El monto no puede ser negativo, se recibió: {amount}.")


class CurrencyMismatchError(DomainError):
    """Se intentó operar sobre montos con monedas distintas."""

    def __init__(self, currency_a: str, currency_b: str) -> None:
        self.currency_a = currency_a
        self.currency_b = currency_b
        super().__init__(
            f"No se pueden combinar montos en monedas distintas: "
            f"'{currency_a}' vs '{currency_b}'."
        )


class PurchaseOrderNotFoundError(DomainError):
    """No existe una orden de compra con el identificador solicitado."""

    def __init__(self, order_id: object) -> None:
        self.order_id = order_id
        super().__init__(f"Orden de compra no encontrada: {order_id}.")


class SupplierNotFoundError(DomainError):
    """No existe un proveedor con el identificador solicitado."""

    def __init__(self, supplier_id: object) -> None:
        self.supplier_id = supplier_id
        super().__init__(f"Proveedor no encontrado: {supplier_id}.")


class UnauthorizedActionError(DomainError):
    """El actor no tiene permisos para ejecutar la acción solicitada."""

    def __init__(self, action: str, role: str) -> None:
        self.action = action
        self.role = role
        super().__init__(f"El rol '{role}' no está autorizado para '{action}'.")


class ApprovalThresholdExceededError(DomainError):
    """El monto de la orden excede lo que el aprobador puede autorizar."""

    def __init__(self, order_total: object, max_allowed: object) -> None:
        self.order_total = order_total
        self.max_allowed = max_allowed
        super().__init__(
            f"El total de la orden ({order_total}) excede el máximo autorizable "
            f"({max_allowed}) para este rol."
        )
