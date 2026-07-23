"""Value Object: LineItem.

Representa una línea de ítem dentro de una Orden de Compra. Es inmutable:
cualquier "modificación" produce una nueva instancia, y la modificación de
líneas de una orden se hace reconstruyendo la lista completa dentro del
agregado `PurchaseOrder` (que es el único punto de entrada para mutar
el estado del negocio).
"""

from __future__ import annotations

from dataclasses import dataclass

from purchase_orders.domain.exceptions.domain_exceptions import (
    InvalidLineItemQuantityError,
)
from purchase_orders.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class LineItem:
    sku: str
    description: str
    quantity: int
    unit_price: Money

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise InvalidLineItemQuantityError(self.quantity)

    @property
    def subtotal(self) -> Money:
        return self.unit_price * self.quantity
