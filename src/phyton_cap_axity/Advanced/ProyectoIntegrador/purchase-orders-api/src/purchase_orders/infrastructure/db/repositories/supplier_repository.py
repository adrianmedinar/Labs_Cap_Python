"""Adaptador: SqlAlchemySupplierRepository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from purchase_orders.domain.entities.supplier import Supplier
from purchase_orders.domain.ports.supplier_repository import SupplierRepository
from purchase_orders.infrastructure.db.models import SupplierModel


def _to_domain(model: SupplierModel) -> Supplier:
    return Supplier(
        id=model.id,
        name=model.name,
        tax_id=model.tax_id,
        email=model.email,
        is_active=model.is_active,
    )


class SqlAlchemySupplierRepository(SupplierRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, supplier: Supplier) -> None:
        model = SupplierModel(
            id=supplier.id,
            name=supplier.name,
            tax_id=supplier.tax_id,
            email=supplier.email,
            is_active=supplier.is_active,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, supplier_id: UUID) -> Supplier | None:
        stmt = select(SupplierModel).where(SupplierModel.id == supplier_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Supplier]:
        stmt = (
            select(SupplierModel)
            .where(SupplierModel.is_active.is_(True))
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_to_domain(m) for m in result.scalars().all()]
