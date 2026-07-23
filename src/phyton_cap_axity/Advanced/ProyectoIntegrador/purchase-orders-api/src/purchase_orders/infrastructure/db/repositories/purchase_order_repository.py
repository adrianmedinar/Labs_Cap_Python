"""Adaptador: SQLAlchemyPurchaseOrderRepository.

Implementa el puerto `PurchaseOrderRepository` usando SQLAlchemy async.
Traduce entre el agregado de dominio `PurchaseOrder` y el modelo ORM
`PurchaseOrderModel`. Esta es la ÚNICA capa que conoce ambos mundos.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from purchase_orders.domain.entities.purchase_order import PurchaseOrder
from purchase_orders.domain.ports.purchase_order_repository import (
    PurchaseOrderRepository,
)
from purchase_orders.domain.value_objects.line_item import LineItem
from purchase_orders.domain.value_objects.money import Money
from purchase_orders.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)
from purchase_orders.infrastructure.db.models import LineItemModel, PurchaseOrderModel


def _to_domain(model: PurchaseOrderModel) -> PurchaseOrder:
    return PurchaseOrder(
        id=model.id,
        supplier_id=model.supplier_id,
        currency=model.currency,
        status=PurchaseOrderStatus(model.status),
        requested_by=model.requested_by,
        approved_by=model.approved_by,
        rejection_reason=model.rejection_reason,
        created_at=model.created_at,
        updated_at=model.updated_at,
        version=model.version,
        line_items=[
            LineItem(
                sku=li.sku,
                description=li.description,
                quantity=li.quantity,
                unit_price=Money(li.unit_price, model.currency),
            )
            for li in model.line_items
        ],
    )


def _line_items_to_models(
    order: PurchaseOrder, purchase_order_id: UUID
) -> list[LineItemModel]:
    return [
        LineItemModel(
            id=uuid4(),
            purchase_order_id=purchase_order_id,
            sku=li.sku,
            description=li.description,
            quantity=li.quantity,
            unit_price=li.unit_price.amount,
        )
        for li in order.line_items
    ]


class ConcurrentModificationError(Exception):
    """La orden fue modificada por otro proceso desde que se leyó."""

    def __init__(self, order_id: UUID) -> None:
        super().__init__(
            f"La orden {order_id} fue modificada concurrentemente; "
            "vuelva a cargarla e intente de nuevo."
        )


class SqlAlchemyPurchaseOrderRepository(PurchaseOrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Registra, por request/UoW, la versión con la que se leyó cada
        # orden. Permite detectar escrituras concurrentes en `update()`
        # sin necesitar que el puerto exponga un parámetro extra.
        self._loaded_versions: dict[UUID, int] = {}

    async def add(self, order: PurchaseOrder) -> None:
        model = PurchaseOrderModel(
            id=order.id,
            supplier_id=order.supplier_id,
            status=order.status.value,
            currency=order.currency,
            requested_by=order.requested_by,
            approved_by=order.approved_by,
            rejection_reason=order.rejection_reason,
            version=order.version,
            line_items=_line_items_to_models(order, order.id),
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, order_id: UUID) -> PurchaseOrder | None:
        stmt = select(PurchaseOrderModel).where(PurchaseOrderModel.id == order_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        self._loaded_versions[order_id] = model.version
        return _to_domain(model)

    async def update(self, order: PurchaseOrder) -> None:
        stmt = select(PurchaseOrderModel).where(PurchaseOrderModel.id == order.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"No se encontró la orden {order.id} para actualizar.")

        # Control de concurrencia optimista: comparamos la versión que
        # había en BD cuando se leyó el agregado (registrada en get_by_id)
        # contra la versión actual en BD. Si difieren, alguien más escribió
        # entre medias y rechazamos esta actualización.
        expected_version = self._loaded_versions.get(order.id)
        if expected_version is not None and model.version != expected_version:
            raise ConcurrentModificationError(order.id)

        model.status = order.status.value
        model.approved_by = order.approved_by
        model.rejection_reason = order.rejection_reason
        model.version = order.version
        model.line_items = _line_items_to_models(order, order.id)

        await self._session.flush()

    async def list_by_status(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[PurchaseOrder]:
        stmt = select(PurchaseOrderModel)
        if status:
            stmt = stmt.where(PurchaseOrderModel.status == status)
        stmt = (
            stmt.limit(limit)
            .offset(offset)
            .order_by(PurchaseOrderModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_to_domain(m) for m in result.scalars().all()]

    async def list_by_supplier(
        self, supplier_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[PurchaseOrder]:
        stmt = (
            select(PurchaseOrderModel)
            .where(PurchaseOrderModel.supplier_id == supplier_id)
            .limit(limit)
            .offset(offset)
            .order_by(PurchaseOrderModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_to_domain(m) for m in result.scalars().all()]
