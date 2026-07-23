"""Pruebas unitarias: casos de uso de Órdenes de Compra (con fakes).

Estas pruebas verifican la ORQUESTACIÓN de los casos de uso (¿llaman al
repositorio correcto?, ¿hacen commit?, ¿traducen bien el DTO?), no las
reglas de negocio del agregado (eso ya está cubierto en
`tests/unit/domain/test_purchase_order.py`). Por eso usamos fakes en
memoria en vez de una base de datos real.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from purchase_orders.application.dtos.purchase_order_dto import (
    ApprovePurchaseOrderCommand,
    CreatePurchaseOrderCommand,
    LineItemCommand,
    RejectPurchaseOrderCommand,
)
from purchase_orders.application.exceptions import ResourceNotFoundError
from purchase_orders.application.use_cases.approve_purchase_order import (
    ApprovePurchaseOrderUseCase,
)
from purchase_orders.application.use_cases.create_purchase_order import (
    CreatePurchaseOrderUseCase,
)
from purchase_orders.application.use_cases.purchase_order_transitions import (
    CancelPurchaseOrderUseCase,
)
from purchase_orders.application.use_cases.query_purchase_orders import (
    GetPurchaseOrderUseCase,
    ListPurchaseOrdersUseCase,
)
from purchase_orders.application.use_cases.reject_purchase_order import (
    RejectPurchaseOrderUseCase,
)
from purchase_orders.application.use_cases.submit_purchase_order import (
    SubmitPurchaseOrderUseCase,
)
from purchase_orders.domain.entities.supplier import Supplier
from purchase_orders.domain.exceptions.domain_exceptions import (
    ApprovalThresholdExceededError,
)
from tests.support.fakes import FakeUnitOfWork

pytestmark = pytest.mark.unit


async def _seed_supplier(uow: FakeUnitOfWork) -> Supplier:
    supplier = Supplier(name="Acme Corp", tax_id="RFC-1", email="v@acme.com")
    await uow.suppliers.add(supplier)
    return supplier


def _create_command(supplier_id, **overrides) -> CreatePurchaseOrderCommand:
    defaults: dict = {
        "supplier_id": supplier_id,
        "requested_by": "jane",
        "currency": "USD",
        "line_items": [
            LineItemCommand(
                sku="SKU-1", description="Laptop", quantity=2, unit_price="1500.00"
            )
        ],
    }
    defaults.update(overrides)
    return CreatePurchaseOrderCommand(**defaults)


class TestCreatePurchaseOrderUseCase:
    async def test_crea_orden_y_hace_commit(self) -> None:
        uow = FakeUnitOfWork()
        supplier = await _seed_supplier(uow)

        result = await CreatePurchaseOrderUseCase(uow).execute(
            _create_command(supplier.id)
        )

        assert result.status == "DRAFT"
        assert result.total == "3000.00"
        assert uow.committed is True

    async def test_rechaza_si_proveedor_no_existe(self) -> None:
        uow = FakeUnitOfWork()
        with pytest.raises(ResourceNotFoundError):
            await CreatePurchaseOrderUseCase(uow).execute(_create_command(uuid4()))


class TestSubmitPurchaseOrderUseCase:
    async def test_transiciona_a_pending_approval(self) -> None:
        uow = FakeUnitOfWork()
        supplier = await _seed_supplier(uow)
        created = await CreatePurchaseOrderUseCase(uow).execute(
            _create_command(supplier.id)
        )

        result = await SubmitPurchaseOrderUseCase(uow).execute(created.id)

        assert result.status == "PENDING_APPROVAL"

    async def test_rechaza_si_orden_no_existe(self) -> None:
        uow = FakeUnitOfWork()
        with pytest.raises(ResourceNotFoundError):
            await SubmitPurchaseOrderUseCase(uow).execute(uuid4())


class TestApprovePurchaseOrderUseCase:
    async def test_aprueba_con_rol_valido_dentro_del_limite(self) -> None:
        uow = FakeUnitOfWork()
        supplier = await _seed_supplier(uow)
        created = await CreatePurchaseOrderUseCase(uow).execute(
            _create_command(supplier.id)
        )
        await SubmitPurchaseOrderUseCase(uow).execute(created.id)

        result = await ApprovePurchaseOrderUseCase(uow).execute(
            ApprovePurchaseOrderCommand(
                order_id=created.id,
                approved_by="manager",
                approver_role="approver_senior",
            )
        )

        assert result.status == "APPROVED"
        assert result.approved_by == "manager"

    async def test_rechaza_si_excede_limite_del_rol(self) -> None:
        uow = FakeUnitOfWork()
        supplier = await _seed_supplier(uow)
        # 1 * 999999.00 excede el límite de approver_junior (5000.00)
        big_command = _create_command(
            supplier.id,
            line_items=[
                LineItemCommand(
                    sku="SKU-1",
                    description="Servidor",
                    quantity=1,
                    unit_price="999999.00",
                )
            ],
        )
        created = await CreatePurchaseOrderUseCase(uow).execute(big_command)
        await SubmitPurchaseOrderUseCase(uow).execute(created.id)

        with pytest.raises(ApprovalThresholdExceededError):
            await ApprovePurchaseOrderUseCase(uow).execute(
                ApprovePurchaseOrderCommand(
                    order_id=created.id,
                    approved_by="junior_manager",
                    approver_role="approver_junior",
                )
            )


class TestRejectPurchaseOrderUseCase:
    async def test_rechaza_orden_con_motivo(self) -> None:
        uow = FakeUnitOfWork()
        supplier = await _seed_supplier(uow)
        created = await CreatePurchaseOrderUseCase(uow).execute(
            _create_command(supplier.id)
        )
        await SubmitPurchaseOrderUseCase(uow).execute(created.id)

        result = await RejectPurchaseOrderUseCase(uow).execute(
            RejectPurchaseOrderCommand(
                order_id=created.id, reason="Presupuesto insuficiente"
            )
        )

        assert result.status == "REJECTED"
        assert result.rejection_reason == "Presupuesto insuficiente"


class TestCancelPurchaseOrderUseCase:
    async def test_cancela_orden_en_draft(self) -> None:
        uow = FakeUnitOfWork()
        supplier = await _seed_supplier(uow)
        created = await CreatePurchaseOrderUseCase(uow).execute(
            _create_command(supplier.id)
        )

        result = await CancelPurchaseOrderUseCase(uow).execute(created.id)

        assert result.status == "CANCELLED"


class TestQueryPurchaseOrders:
    async def test_get_retorna_la_orden_correcta(self) -> None:
        uow = FakeUnitOfWork()
        supplier = await _seed_supplier(uow)
        created = await CreatePurchaseOrderUseCase(uow).execute(
            _create_command(supplier.id)
        )

        result = await GetPurchaseOrderUseCase(uow).execute(created.id)

        assert result.id == created.id

    async def test_get_lanza_not_found_si_no_existe(self) -> None:
        uow = FakeUnitOfWork()
        with pytest.raises(ResourceNotFoundError):
            await GetPurchaseOrderUseCase(uow).execute(uuid4())

    async def test_list_filtra_por_status(self) -> None:
        uow = FakeUnitOfWork()
        supplier = await _seed_supplier(uow)
        order_a = await CreatePurchaseOrderUseCase(uow).execute(
            _create_command(supplier.id)
        )
        await CreatePurchaseOrderUseCase(uow).execute(_create_command(supplier.id))
        await SubmitPurchaseOrderUseCase(uow).execute(order_a.id)

        drafts = await ListPurchaseOrdersUseCase(uow).execute(status="DRAFT")
        pending = await ListPurchaseOrdersUseCase(uow).execute(
            status="PENDING_APPROVAL"
        )

        assert len(drafts) == 1
        assert len(pending) == 1
        assert pending[0].id == order_a.id

    async def test_list_filtra_por_supplier(self) -> None:
        uow = FakeUnitOfWork()
        supplier_a = await _seed_supplier(uow)
        supplier_b = Supplier(name="Other Corp", tax_id="RFC-2", email="o@other.com")
        await uow.suppliers.add(supplier_b)

        await CreatePurchaseOrderUseCase(uow).execute(_create_command(supplier_a.id))
        await CreatePurchaseOrderUseCase(uow).execute(_create_command(supplier_b.id))

        results = await ListPurchaseOrdersUseCase(uow).execute(
            supplier_id=supplier_a.id
        )

        assert len(results) == 1
        assert results[0].supplier_id == supplier_a.id
