"""
TDD - Historia: "Transiciones de estado válidas para una Order"

"""

from app.core.order_rules import can_transition
from app.models.order import OrderStatus


class TestTransicionesValidas:
    def test_pending_a_paid_es_valida(self):
        assert can_transition(OrderStatus.PENDING, OrderStatus.PAID) is True

    def test_paid_a_shipped_es_valida(self):
        assert can_transition(OrderStatus.PAID, OrderStatus.SHIPPED) is True

    def test_pending_a_cancelled_es_valida(self):
        assert can_transition(OrderStatus.PENDING, OrderStatus.CANCELLED) is True

    def test_paid_a_cancelled_es_valida(self):
        assert can_transition(OrderStatus.PAID, OrderStatus.CANCELLED) is True

    def test_mismo_estado_es_valida_noop(self):
        for status in OrderStatus:
            assert can_transition(status, status) is True


class TestTransicionesInvalidas:
    def test_shipped_no_puede_cambiar_a_nada(self):
        for destino in OrderStatus:
            if destino == OrderStatus.SHIPPED:
                continue
            assert can_transition(OrderStatus.SHIPPED, destino) is False

    def test_cancelled_no_puede_cambiar_a_nada(self):
        for destino in OrderStatus:
            if destino == OrderStatus.CANCELLED:
                continue
            assert can_transition(OrderStatus.CANCELLED, destino) is False

    def test_no_se_puede_retroceder_paid_a_pending(self):
        assert can_transition(OrderStatus.PAID, OrderStatus.PENDING) is False

    def test_pending_no_puede_saltar_a_shipped(self):
        assert can_transition(OrderStatus.PENDING, OrderStatus.SHIPPED) is False
