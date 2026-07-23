"""Entidad: Supplier (Proveedor).

Entidad de soporte referenciada por PurchaseOrder mediante `supplier_id`.
Se mantiene deliberadamente simple: el proveedor es un agregado independiente
y PurchaseOrder solo guarda su identidad (buena práctica DDD para evitar
agregados sobre-acoplados).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Supplier:
    name: str
    tax_id: str
    email: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True
