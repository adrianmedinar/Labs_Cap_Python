"""Pruebas unitarias: agregado PurchaseOrder.

El foco de estas pruebas es el CORAZÓN del negocio: la máquina de estados
y los invariantes del agregado, sin ninguna dependencia externa.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from purchase_orders.domain.entities.purchase_order import PurchaseOrder
from purchase_orders.domain.exceptions.domain_exceptions import (
    ApprovalThresholdExceededError,
    EmptyPurchaseOrderError,
    InvalidPurchaseOrderStateError,
)
from purchase_orders.domain.value_objects.line_item import LineItem
from purchase_orders.domain.value_objects.money import Money
from purchase_orders.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
)

pytestmark = pytest.mark.unit


def _make_line_item(
    sku: str = "SKU-1", price: str = "100.00", qty: int = 1
) -> LineItem:
    return LineItem(
        sku=sku,
        description="Item de prueba",
        quantity=qty,
        unit_price=Money.from_str(price),
    )


def _make_order(*line_items: LineItem, currency: str = "MXN") -> PurchaseOrder:
    items = list(line_items) or [_make_line_item()]
    return PurchaseOrder.create(
        supplier_id=uuid4(), requested_by="tester", line_items=items, currency=currency
    )


class TestCreacion:
    def test_crea_orden_en_estado_draft(self) -> None:
        order = _make_order()
        assert order.status == PurchaseOrderStatus.DRAFT

    def test_rechaza_orden_sin_items(self) -> None:
        with pytest.raises(EmptyPurchaseOrderError):
            PurchaseOrder.create(
                supplier_id=uuid4(), requested_by="tester", line_items=[]
            )

    def test_total_es_suma_de_subtotales(self) -> None:
        order = _make_order(
            _make_line_item("SKU-1", "100.00", 2),  # 200.00
            _make_line_item("SKU-2", "50.00", 3),  # 150.00
        )
        assert order.total == Money.from_str("350.00")

    def test_version_inicial_es_uno(self) -> None:
        assert _make_order().version == 1


class TestEdicionEnDraft:
    def test_puede_agregar_item_en_draft(self) -> None:
        order = _make_order()
        order.add_line_item(_make_line_item("SKU-2"))
        assert len(order.line_items) == 2

    def test_puede_quitar_item_en_draft(self) -> None:
        order = _make_order(_make_line_item("SKU-1"), _make_line_item("SKU-2"))
        order.remove_line_item("SKU-2")
        assert [li.sku for li in order.line_items] == ["SKU-1"]

    def test_no_puede_quedar_vacia_al_quitar_ultimo_item(self) -> None:
        order = _make_order(_make_line_item("SKU-1"))
        with pytest.raises(EmptyPurchaseOrderError):
            order.remove_line_item("SKU-1")

    def test_no_puede_editar_fuera_de_draft(self) -> None:
        order = _make_order()
        order.submit()
        with pytest.raises(InvalidPurchaseOrderStateError):
            order.add_line_item(_make_line_item("SKU-2"))

    def test_editar_incrementa_version(self) -> None:
        order = _make_order()
        initial_version = order.version
        order.add_line_item(_make_line_item("SKU-2"))
        assert order.version == initial_version + 1


class TestCicloDeVidaCompleto:
    def test_flujo_feliz_completo(self) -> None:
        order = _make_order()
        order.submit()
        assert order.status == PurchaseOrderStatus.PENDING_APPROVAL

        order.approve(
            approved_by="manager", approver_max_amount=Money.from_str("10000.00")
        )
        assert order.status == PurchaseOrderStatus.APPROVED
        assert order.approved_by == "manager"

        order.send_to_supplier()
        assert order.status == PurchaseOrderStatus.SENT_TO_SUPPLIER

        order.confirm_receipt()
        assert order.status == PurchaseOrderStatus.RECEIVED

        order.close()
        assert order.status == PurchaseOrderStatus.CLOSED

    def test_flujo_de_rechazo(self) -> None:
        order = _make_order()
        order.submit()
        order.reject(reason="Precio fuera de presupuesto")
        assert order.status == PurchaseOrderStatus.REJECTED
        assert order.rejection_reason == "Precio fuera de presupuesto"

    @pytest.mark.parametrize(
        "setup_status",
        ["draft", "pending_approval", "approved"],
    )
    def test_cancelacion_desde_estados_permitidos(self, setup_status: str) -> None:
        order = _make_order()
        if setup_status in {"pending_approval", "approved"}:
            order.submit()
        if setup_status == "approved":
            order.approve(
                approved_by="m", approver_max_amount=Money.from_str("10000.00")
            )

        order.cancel()
        assert order.status == PurchaseOrderStatus.CANCELLED

    def test_no_puede_cancelar_orden_ya_enviada_al_proveedor(self) -> None:
        order = _make_order()
        order.submit()
        order.approve(approved_by="m", approver_max_amount=Money.from_str("10000.00"))
        order.send_to_supplier()
        with pytest.raises(InvalidPurchaseOrderStateError):
            order.cancel()

    def test_no_puede_saltarse_estados(self) -> None:
        order = _make_order()
        with pytest.raises(InvalidPurchaseOrderStateError):
            order.approve(
                approved_by="m", approver_max_amount=Money.from_str("10000.00")
            )

    def test_no_puede_re_enviar_orden_cerrada(self) -> None:
        order = _make_order()
        order.submit()
        order.approve(approved_by="m", approver_max_amount=Money.from_str("10000.00"))
        order.send_to_supplier()
        order.confirm_receipt()
        order.close()
        with pytest.raises(InvalidPurchaseOrderStateError):
            order.submit()


class TestReglaDeAprobacion:
    def test_rechaza_aprobacion_que_excede_limite(self) -> None:
        order = _make_order(_make_line_item("SKU-1", "9999.00"))
        order.submit()
        with pytest.raises(ApprovalThresholdExceededError):
            order.approve(
                approved_by="junior", approver_max_amount=Money.from_str("100.00")
            )

    def test_permite_aprobacion_igual_al_limite(self) -> None:
        order = _make_order(_make_line_item("SKU-1", "100.00"))
        order.submit()
        # No debe lanzar: el total es exactamente igual al límite.
        order.approve(
            approved_by="junior", approver_max_amount=Money.from_str("100.00")
        )
        assert order.status == PurchaseOrderStatus.APPROVED
