"""Caso de uso: Crear Proveedor."""

from __future__ import annotations

from purchase_orders.application.dtos.common_dto import (
    CreateSupplierCommand,
    SupplierResult,
)
from purchase_orders.application.mappers import supplier_to_result
from purchase_orders.domain.entities.supplier import Supplier
from purchase_orders.domain.ports.unit_of_work import UnitOfWork


class CreateSupplierUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateSupplierCommand) -> SupplierResult:
        async with self._uow as uow:
            supplier = Supplier(
                name=command.name, tax_id=command.tax_id, email=command.email
            )
            await uow.suppliers.add(supplier)
            await uow.commit()
            return supplier_to_result(supplier)
