"""Pruebas de integración: repositorios SQLAlchemy contra una BD real
(SQLite en memoria). A diferencia de las pruebas unitarias de aplicación
(que usan fakes), aquí verificamos que el MAPEO objeto-relacional y las
consultas SQL realmente funcionan.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from purchase_orders.domain.entities.purchase_order import PurchaseOrder
from purchase_orders.domain.entities.supplier import Supplier
from purchase_orders.domain.value_objects.line_item import LineItem
from purchase_orders.domain.value_objects.money import Money
from purchase_orders.infrastructure.db.repositories.purchase_order_repository import (
    ConcurrentModificationError,
)
from purchase_orders.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def _seed_supplier(
    session_factory: async_sessionmaker[AsyncSession],
) -> Supplier:
    supplier = Supplier(
        name="Acme Corp", tax_id=f"RFC-{uuid4().hex[:8]}", email="v@acme.com"
    )
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.suppliers.add(supplier)
        await uow.commit()
    return supplier


class TestSupplierRepository:
    async def test_add_y_get_by_id(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        supplier = await _seed_supplier(session_factory)

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            found = await uow.suppliers.get_by_id(supplier.id)

        assert found is not None
        assert found.name == "Acme Corp"

    async def test_get_by_id_retorna_none_si_no_existe(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            found = await uow.suppliers.get_by_id(uuid4())
        assert found is None

    async def test_list_active_excluye_inactivos(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        active = await _seed_supplier(session_factory)
        inactive = Supplier(
            name="Inactive Corp",
            tax_id=f"RFC-{uuid4().hex[:8]}",
            email="i@corp.com",
            is_active=False,
        )
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.suppliers.add(inactive)
            await uow.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            results = await uow.suppliers.list_active()

        ids = {s.id for s in results}
        assert active.id in ids
        assert inactive.id not in ids


class TestPurchaseOrderRepository:
    async def test_add_persiste_orden_con_line_items(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        supplier = await _seed_supplier(session_factory)
        order = PurchaseOrder.create(
            supplier_id=supplier.id,
            requested_by="jane",
            line_items=[
                LineItem(
                    sku="SKU-1",
                    description="Laptop",
                    quantity=2,
                    unit_price=Money.from_str("1500.00"),
                ),
                LineItem(
                    sku="SKU-2",
                    description="Mouse",
                    quantity=5,
                    unit_price=Money.from_str("20.00"),
                ),
            ],
        )
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.purchase_orders.add(order)
            await uow.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            found = await uow.purchase_orders.get_by_id(order.id)

        assert found is not None
        assert len(found.line_items) == 2
        assert found.total == Money.from_str("3100.00")

    async def test_update_persiste_cambio_de_estado(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        supplier = await _seed_supplier(session_factory)
        order = PurchaseOrder.create(
            supplier_id=supplier.id,
            requested_by="jane",
            line_items=[
                LineItem(
                    sku="SKU-1",
                    description="Item",
                    quantity=1,
                    unit_price=Money.from_str("10.00"),
                )
            ],
        )
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.purchase_orders.add(order)
            await uow.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            loaded = await uow.purchase_orders.get_by_id(order.id)
            loaded.submit()
            await uow.purchase_orders.update(loaded)
            await uow.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            reloaded = await uow.purchase_orders.get_by_id(order.id)

        assert reloaded.status.value == "PENDING_APPROVAL"
        assert reloaded.version == 2

    async def test_modificacion_concurrente_lanza_excepcion(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        supplier = await _seed_supplier(session_factory)
        order = PurchaseOrder.create(
            supplier_id=supplier.id,
            requested_by="jane",
            line_items=[
                LineItem(
                    sku="SKU-1",
                    description="Item",
                    quantity=1,
                    unit_price=Money.from_str("10.00"),
                )
            ],
        )
        order.submit()  # PENDING_APPROVAL: desde aquí approve/reject son ambas válidas
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.purchase_orders.add(order)
            await uow.commit()

        # Dos "procesos" (UoW independientes, abiertos simultáneamente)
        # leen la MISMA orden antes de que ninguno haya escrito todavía.
        async with (
            SqlAlchemyUnitOfWork(session_factory) as uow_a,
            SqlAlchemyUnitOfWork(session_factory) as uow_b,
        ):
            order_a = await uow_a.purchase_orders.get_by_id(order.id)
            order_b = await uow_b.purchase_orders.get_by_id(order.id)

            # El proceso A aprueba primero y confirma con éxito.
            order_a.approve(
                approved_by="m", approver_max_amount=Money.from_str("10000.00")
            )
            await uow_a.purchase_orders.update(order_a)
            await uow_a.commit()

            # El proceso B intenta rechazar sobre una versión que ya quedó
            # obsoleta en BD (A la modificó entre medias) -> se rechaza.
            order_b.reject(reason="tarde")
            with pytest.raises(ConcurrentModificationError):
                await uow_b.purchase_orders.update(order_b)

    async def test_list_by_status(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        supplier = await _seed_supplier(session_factory)
        order = PurchaseOrder.create(
            supplier_id=supplier.id,
            requested_by="jane",
            line_items=[
                LineItem(
                    sku="SKU-1",
                    description="Item",
                    quantity=1,
                    unit_price=Money.from_str("10.00"),
                )
            ],
        )
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.purchase_orders.add(order)
            await uow.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            drafts = await uow.purchase_orders.list_by_status("DRAFT")
            approved = await uow.purchase_orders.list_by_status("APPROVED")

        assert any(o.id == order.id for o in drafts)
        assert not any(o.id == order.id for o in approved)

    async def test_list_by_supplier(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        supplier = await _seed_supplier(session_factory)
        order = PurchaseOrder.create(
            supplier_id=supplier.id,
            requested_by="jane",
            line_items=[
                LineItem(
                    sku="SKU-1",
                    description="Item",
                    quantity=1,
                    unit_price=Money.from_str("10.00"),
                )
            ],
        )
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.purchase_orders.add(order)
            await uow.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            results = await uow.purchase_orders.list_by_supplier(supplier.id)

        assert len(results) == 1
        assert results[0].id == order.id
