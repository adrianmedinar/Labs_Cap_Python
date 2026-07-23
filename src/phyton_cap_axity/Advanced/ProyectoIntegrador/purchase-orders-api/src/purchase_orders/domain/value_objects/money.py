"""Value Object: Money.

Representa un monto monetario inmutable con su moneda. Encapsula las reglas
de negocio para operar montos de forma segura (evita mezclar monedas,
evita montos negativos, controla precisión decimal).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from purchase_orders.domain.exceptions.domain_exceptions import (
    CurrencyMismatchError,
    InvalidMoneyAmountError,
)

_CENTS = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """Monto monetario inmutable. Siempre normalizado a 2 decimales."""

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        normalized_amount = Decimal(self.amount).quantize(
            _CENTS, rounding=ROUND_HALF_UP
        )
        if normalized_amount < Decimal("0"):
            raise InvalidMoneyAmountError(normalized_amount)
        object.__setattr__(self, "amount", normalized_amount)
        object.__setattr__(self, "currency", self.currency.upper())

    @classmethod
    def zero(cls, currency: str = "USD") -> Money:
        return cls(Decimal("0"), currency)

    @classmethod
    def from_str(cls, amount: str, currency: str = "USD") -> Money:
        return cls(Decimal(amount), currency)

    def _ensure_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(self.currency, other.currency)

    def __add__(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: int) -> Money:
        if not isinstance(factor, int):
            return NotImplemented
        return Money(self.amount * factor, self.currency)

    def __gt__(self, other: Money) -> bool:
        self._ensure_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._ensure_same_currency(other)
        return self.amount >= other.amount

    def __lt__(self, other: Money) -> bool:
        self._ensure_same_currency(other)
        return self.amount < other.amount

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
