"""Pruebas unitarias: Money (value object)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from purchase_orders.domain.exceptions.domain_exceptions import (
    CurrencyMismatchError,
    InvalidMoneyAmountError,
)
from purchase_orders.domain.value_objects.money import Money

pytestmark = pytest.mark.unit


class TestMoneyCreation:
    def test_normaliza_a_dos_decimales(self) -> None:
        money = Money.from_str("10.999")
        assert money.amount == Decimal("11.00")

    def test_normaliza_moneda_a_mayusculas(self) -> None:
        money = Money.from_str("10.00", "usd")
        assert money.currency == "USD"

    def test_rechaza_montos_negativos(self) -> None:
        with pytest.raises(InvalidMoneyAmountError):
            Money.from_str("-5.00")

    def test_zero_construye_monto_cero(self) -> None:
        money = Money.zero("EUR")
        assert money.amount == Decimal("0.00")
        assert money.currency == "EUR"


class TestMoneyArithmetic:
    def test_suma_montos_misma_moneda(self) -> None:
        result = Money.from_str("10.00") + Money.from_str("5.50")
        assert result == Money.from_str("15.50")

    def test_resta_montos_misma_moneda(self) -> None:
        result = Money.from_str("10.00") - Money.from_str("3.00")
        assert result == Money.from_str("7.00")

    def test_multiplica_por_entero(self) -> None:
        result = Money.from_str("10.00") * 3
        assert result == Money.from_str("30.00")

    def test_suma_rechaza_monedas_distintas(self) -> None:
        with pytest.raises(CurrencyMismatchError):
            Money.from_str("10.00", "USD") + Money.from_str("10.00", "EUR")

    def test_resta_rechaza_monedas_distintas(self) -> None:
        with pytest.raises(CurrencyMismatchError):
            Money.from_str("10.00", "USD") - Money.from_str("10.00", "EUR")

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            ("10.00", "5.00", True),
            ("5.00", "10.00", False),
            ("5.00", "5.00", False),
        ],
    )
    def test_comparacion_mayor_que(self, a: str, b: str, expected: bool) -> None:
        assert (Money.from_str(a) > Money.from_str(b)) is expected

    def test_comparacion_rechaza_monedas_distintas(self) -> None:
        with pytest.raises(CurrencyMismatchError):
            _ = Money.from_str("10.00", "USD") > Money.from_str("5.00", "EUR")

    def test_money_es_inmutable(self) -> None:
        money = Money.from_str("10.00")
        with pytest.raises(AttributeError):
            money.amount = Decimal("99.00")  # type: ignore[misc]
