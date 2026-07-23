"""Pruebas unitarias: LineItem (value object)."""

from __future__ import annotations

import pytest

from purchase_orders.domain.exceptions.domain_exceptions import (
    InvalidLineItemQuantityError,
)
from purchase_orders.domain.value_objects.line_item import LineItem
from purchase_orders.domain.value_objects.money import Money

pytestmark = pytest.mark.unit


def test_subtotal_multiplica_precio_por_cantidad() -> None:
    item = LineItem(
        sku="SKU-1",
        description="Laptop",
        quantity=3,
        unit_price=Money.from_str("100.00"),
    )
    assert item.subtotal == Money.from_str("300.00")


@pytest.mark.parametrize("invalid_quantity", [0, -1, -100])
def test_rechaza_cantidad_no_positiva(invalid_quantity: int) -> None:
    with pytest.raises(InvalidLineItemQuantityError):
        LineItem(
            sku="SKU-1",
            description="Laptop",
            quantity=invalid_quantity,
            unit_price=Money.from_str("100.00"),
        )


def test_line_item_es_inmutable() -> None:
    item = LineItem(
        sku="SKU-1",
        description="Laptop",
        quantity=1,
        unit_price=Money.from_str("10.00"),
    )
    with pytest.raises(AttributeError):
        item.quantity = 5  # type: ignore[misc]
