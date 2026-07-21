"""
Reglas de negocio de transición de estados de una Order.

Máquina de estados:

    pending ---> paid ---> shipped
       |          |
       v          v
    cancelled  cancelled

`shipped` y `cancelled` son estados terminales: no admiten más transiciones.
"""
from app.models.order import OrderStatus

# Mapa de transiciones permitidas: estado actual -> conjunto de estados destino válidos.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.SHIPPED},
    OrderStatus.CANCELLED: {OrderStatus.CANCELLED},
}


def can_transition(current: OrderStatus, new: OrderStatus) -> bool:
    """Indica si es válido pasar del estado `current` al estado `new`."""
    return new in _ALLOWED_TRANSITIONS[current]
