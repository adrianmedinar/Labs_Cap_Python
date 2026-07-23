"""Pruebas unitarias: máquina de estados PurchaseOrderStatus."""

from __future__ import annotations

import pytest

from purchase_orders.domain.value_objects.purchase_order_status import (
    PurchaseOrderStatus,
    can_transition,
    is_terminal,
    next_state,
)

pytestmark = pytest.mark.unit


class TestTransicionesValidas:
    @pytest.mark.parametrize(
        ("current", "action", "expected"),
        [
            (PurchaseOrderStatus.DRAFT, "submit", PurchaseOrderStatus.PENDING_APPROVAL),
            (
                PurchaseOrderStatus.PENDING_APPROVAL,
                "approve",
                PurchaseOrderStatus.APPROVED,
            ),
            (
                PurchaseOrderStatus.PENDING_APPROVAL,
                "reject",
                PurchaseOrderStatus.REJECTED,
            ),
            (
                PurchaseOrderStatus.APPROVED,
                "send",
                PurchaseOrderStatus.SENT_TO_SUPPLIER,
            ),
            (
                PurchaseOrderStatus.SENT_TO_SUPPLIER,
                "confirm_receipt",
                PurchaseOrderStatus.RECEIVED,
            ),
            (PurchaseOrderStatus.RECEIVED, "close", PurchaseOrderStatus.CLOSED),
            (PurchaseOrderStatus.DRAFT, "cancel", PurchaseOrderStatus.CANCELLED),
            (
                PurchaseOrderStatus.PENDING_APPROVAL,
                "cancel",
                PurchaseOrderStatus.CANCELLED,
            ),
            (PurchaseOrderStatus.APPROVED, "cancel", PurchaseOrderStatus.CANCELLED),
        ],
    )
    def test_transicion_permitida(
        self, current: PurchaseOrderStatus, action: str, expected: PurchaseOrderStatus
    ) -> None:
        assert can_transition(current, action) is True
        assert next_state(current, action) == expected


class TestTransicionesInvalidas:
    @pytest.mark.parametrize(
        ("current", "action"),
        [
            (PurchaseOrderStatus.DRAFT, "approve"),
            (PurchaseOrderStatus.APPROVED, "submit"),
            (PurchaseOrderStatus.CLOSED, "submit"),
            (PurchaseOrderStatus.REJECTED, "approve"),
            (PurchaseOrderStatus.CANCELLED, "cancel"),
            (PurchaseOrderStatus.SENT_TO_SUPPLIER, "cancel"),
            (PurchaseOrderStatus.RECEIVED, "cancel"),
        ],
    )
    def test_transicion_no_permitida(
        self, current: PurchaseOrderStatus, action: str
    ) -> None:
        assert can_transition(current, action) is False


class TestEstadosTerminales:
    @pytest.mark.parametrize(
        "terminal_status",
        [
            PurchaseOrderStatus.REJECTED,
            PurchaseOrderStatus.CLOSED,
            PurchaseOrderStatus.CANCELLED,
        ],
    )
    def test_estado_terminal(self, terminal_status: PurchaseOrderStatus) -> None:
        assert is_terminal(terminal_status) is True

    @pytest.mark.parametrize(
        "non_terminal_status",
        [
            PurchaseOrderStatus.DRAFT,
            PurchaseOrderStatus.PENDING_APPROVAL,
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.SENT_TO_SUPPLIER,
            PurchaseOrderStatus.RECEIVED,
        ],
    )
    def test_estado_no_terminal(self, non_terminal_status: PurchaseOrderStatus) -> None:
        assert is_terminal(non_terminal_status) is False
