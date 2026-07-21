"""
Tests de propiedades (property-based testing) con Hypothesis.

A diferencia de los tests de ejemplo (que fijan valores concretos), estos
tests definen invariantes que deben cumplirse para *cualquier* entrada
dentro de un dominio, y Hypothesis genera cientos de casos (incluyendo
edge cases) buscando activamente contraejemplos que los rompan.
"""

from app.core.order_rules import can_transition
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate
from hypothesis import given
from hypothesis import strategies as st

# --- Estrategias reutilizables ---
quantity_valida = st.integers(min_value=1, max_value=10_000)
precio_valido = st.floats(
    min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False
)
estado_cualquiera = st.sampled_from(list(OrderStatus))


# =========================================================================
# Propiedades del cálculo de total_price
# =========================================================================
class TestPropiedadesTotalPrice:
    @given(quantity=quantity_valida, unit_price=precio_valido)
    def test_total_price_es_siempre_positivo(self, quantity, unit_price):
        order = Order(item="x", quantity=quantity, unit_price=unit_price)
        assert order.total_price > 0

    @given(quantity=quantity_valida, unit_price=precio_valido)
    def test_total_price_coincide_con_quantity_por_unit_price_redondeado(
        self, quantity, unit_price
    ):
        order = Order(item="x", quantity=quantity, unit_price=unit_price)
        esperado = round(quantity * unit_price, 2)
        assert order.total_price == esperado

    @given(quantity=quantity_valida, unit_price=precio_valido)
    def test_total_price_es_monotono_creciente_en_quantity(self, quantity, unit_price):
        """A mayor cantidad (con mismo precio unitario), el total nunca puede ser menor."""
        order_base = Order(item="x", quantity=quantity, unit_price=unit_price)
        order_mas = Order(item="x", quantity=quantity + 1, unit_price=unit_price)
        assert order_mas.total_price >= order_base.total_price

    @given(quantity=quantity_valida, unit_price=precio_valido)
    def test_schema_orden_create_acepta_todo_el_dominio_valido(
        self, quantity, unit_price
    ):
        """Cualquier combinación dentro del dominio válido debe pasar el schema sin excepción."""
        order_in = OrderCreate(
            item="Producto", quantity=quantity, unit_price=unit_price
        )
        assert order_in.quantity == quantity
        assert order_in.unit_price == unit_price


# =========================================================================
# Propiedades de validación del schema (dominio inválido siempre rechazado)
# =========================================================================
class TestPropiedadesValidacionSchema:
    @given(quantity=st.integers(max_value=0))
    def test_quantity_no_positiva_siempre_rechazada(self, quantity):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OrderCreate(item="x", quantity=quantity, unit_price=10.0)

    @given(unit_price=st.floats(max_value=0, allow_nan=False, allow_infinity=False))
    def test_unit_price_no_positivo_siempre_rechazado(self, unit_price):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OrderCreate(item="x", quantity=1, unit_price=unit_price)

    @given(item=st.text(alphabet=" \t\n", max_size=10))
    def test_item_solo_espacios_siempre_rechazado(self, item):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OrderCreate(item=item, quantity=1, unit_price=10.0)


# =========================================================================
# Propiedades de la máquina de estados (can_transition)
# =========================================================================
class TestPropiedadesTransiciones:
    @given(estado=estado_cualquiera)
    def test_reflexividad_todo_estado_puede_permanecer_igual(self, estado):
        assert can_transition(estado, estado) is True

    @given(destino=estado_cualquiera)
    def test_shipped_es_terminal(self, destino):
        """Ningún destino (salvo el propio) es alcanzable desde 'shipped'."""
        resultado = can_transition(OrderStatus.SHIPPED, destino)
        assert resultado == (destino == OrderStatus.SHIPPED)

    @given(destino=estado_cualquiera)
    def test_cancelled_es_terminal(self, destino):
        resultado = can_transition(OrderStatus.CANCELLED, destino)
        assert resultado == (destino == OrderStatus.CANCELLED)

    @given(origen=estado_cualquiera, destino=estado_cualquiera)
    def test_can_transition_siempre_devuelve_booleano(self, origen, destino):
        """Propiedad de robustez: la función nunca lanza excepción para el dominio del enum."""
        resultado = can_transition(origen, destino)
        assert isinstance(resultado, bool)

    @given(origen=estado_cualquiera, destino=estado_cualquiera)
    def test_no_existen_transiciones_ciclicas_de_vuelta_a_pending(
        self, origen, destino
    ):
        """Invariante de negocio: una vez que sales de 'pending', nunca puedes volver."""
        if origen != OrderStatus.PENDING and destino == OrderStatus.PENDING:
            assert can_transition(origen, destino) is False
