"""
Ejemplo integrador: dataclasses + attrs + pydantic + herencia + composición + dunder methods
=============================================================================================
Dominio: Pedidos de una tienda   (Producto -> LineaPedido -> Pedido)

Capas:
  1) DOMINIO   -> attrs (Producto) y dataclasses (LineaPedido, Pedido): entidades con
                  comportamiento, validaciones y comparaciones.
  2) FRONTERA  -> pydantic (ProductoIn/LineaPedidoIn/PedidoIn/PedidoOut): valida lo que
                  entra, serializa lo que sale, y convierte hacia/desde el dominio.

  3) Ejecutar directamente desde la terminal:

       python datamodel_objects.py

"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List

import attr
from pydantic import BaseModel, ConfigDict, field_validator

# ---------------------------------------------------------------------------
# 1) DOMINIO
# ---------------------------------------------------------------------------


class Entidad:
    """Clase base compartida (HERENCIA): todo lo del dominio tiene un id y un __repr__ base."""

    id: str

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"


def _precio_positivo(instance, atributo, valor):
    """Validador reutilizable para attrs."""
    if valor <= 0:
        raise ValueError(f"El precio debe ser positivo, recibido: {valor}")


@attr.s(auto_attribs=True, frozen=True, eq=True, order=True, repr=False)
class Producto(Entidad):
    """
    Value object inmutable (frozen=True) hecho con attrs.
    - eq=True / order=True -> genera __eq__, __lt__, __gt__, etc. comparando TODOS los
      campos en orden (id, nombre, precio).
    - repr=False -> no genera __repr__ automático; usamos el nuestro, que REUTILIZA
      (extiende) el de Entidad vía super().
    """

    id: str
    nombre: str
    precio: Decimal = attr.ib(validator=_precio_positivo)

    def __repr__(self) -> str:
        return f"{super().__repr__()} {self.nombre} (${self.precio})"


@dataclass
class LineaPedido:
    """
    COMPOSICIÓN: una LineaPedido "tiene un" Producto (no hereda de él).
    Usa __post_init__ para validar y calcular un campo derivado (subtotal).
    """

    producto: Producto
    cantidad: int
    subtotal: Decimal = field(init=False)  # se calcula

    def __post_init__(self):
        if self.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        self.subtotal = self.producto.precio * self.cantidad

    def __repr__(self) -> str:
        return f"{self.cantidad}x {self.producto.nombre} = ${self.subtotal}"


@dataclass(order=True)
class Pedido(Entidad):
    """
    HERENCIA (de Entidad) + COMPOSICIÓN (lista de LineaPedido) + dataclass "order".

    order=True genera __lt__/__le__/__gt__/__ge__ comparando los campos EN ORDEN,
    pero solo los que tengan compare=True (el resto se excluye con compare=False).

    """

    total: Decimal = field(
        init=False, compare=True
    )  # campo derivado, compara por total
    id: str = field(compare=False)
    cliente: str = field(compare=False)
    lineas: List[LineaPedido] = field(default_factory=list, compare=False)
    creado_en: datetime = field(default_factory=datetime.now, compare=False)

    def __post_init__(self):
        self.total = sum((linea.subtotal for linea in self.lineas), Decimal("0"))

    def agregar_linea(self, linea: LineaPedido) -> None:
        self.lineas.append(linea)
        self.total += linea.subtotal  # recalcula el derivado

    def __add__(self, otro: "Pedido") -> "Pedido":
        """Dunder aritmético: combina dos pedidos del mismo cliente en uno solo."""
        if self.cliente != otro.cliente:
            raise ValueError("Solo se pueden combinar pedidos del mismo cliente")
        return Pedido(
            id=f"{self.id}+{otro.id}",
            cliente=self.cliente,
            lineas=self.lineas + otro.lineas,
        )

    def __repr__(self) -> str:
        return f"{super().__repr__()} cliente={self.cliente} total=${self.total}"


# ---------------------------------------------------------------------------
# 2) FRONTERA (Pydantic): validar entradas, serializar salidas
# ---------------------------------------------------------------------------


class ProductoIn(BaseModel):
    """DTO de entrada: valida lo que llega."""

    id: str
    nombre: str
    precio: Decimal

    @field_validator("precio")
    @classmethod
    def precio_positivo(cls, v):
        if v <= 0:
            raise ValueError("El precio debe ser positivo")
        return v

    def a_entidad(self) -> Producto:
        """Convierte el DTO ya validado en la entidad de dominio (attrs)."""
        return Producto(id=self.id, nombre=self.nombre, precio=self.precio)


class LineaPedidoIn(BaseModel):
    producto: ProductoIn
    cantidad: int

    @field_validator("cantidad")
    @classmethod
    def cantidad_positiva(cls, v):
        if v <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        return v

    def a_entidad(self) -> LineaPedido:
        return LineaPedido(producto=self.producto.a_entidad(), cantidad=self.cantidad)


class PedidoIn(BaseModel):
    """DTO de ENTRADA completo: lo que recibirías."""

    id: str
    cliente: str
    lineas: List[LineaPedidoIn]

    def a_entidad(self) -> Pedido:
        pedido = Pedido(id=self.id, cliente=self.cliente, lineas=[])
        for linea_in in self.lineas:
            pedido.agregar_linea(linea_in.a_entidad())
        return pedido


class PedidoOut(BaseModel):
    """DTO de SALIDA: lo que se serializa, es decir, la respuesta."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    cliente: str
    total: Decimal
    cantidad_lineas: int
    creado_en: datetime

    @classmethod
    def desde_entidad(cls, pedido: Pedido) -> "PedidoOut":
        return cls(
            id=pedido.id,
            cliente=pedido.cliente,
            total=pedido.total,
            cantidad_lineas=len(pedido.lineas),
            creado_en=pedido.creado_en,
        )


# ---------------------------------------------------------------------------
# 3) Laboratorio: flujo completo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    datos_entrada = {
        "id": "PED-001",
        "cliente": "Adrian",
        "lineas": [
            {
                "producto": {"id": "P1", "nombre": "Teclado", "precio": "45.00"},
                "cantidad": 2,
            },
            {
                "producto": {"id": "P2", "nombre": "Mouse", "precio": "15.50"},
                "cantidad": 3,
            },
        ],
    }

    print("=" * 70)
    print("1) VALIDACIÓN DE ENTRADA (pydantic)")
    print("=" * 70)
    pedido_in = PedidoIn(**datos_entrada)
    print(pedido_in)

    print("\n" + "=" * 70)
    print("2) CONVERSIÓN A ENTIDAD DE DOMINIO (dataclass + attrs)")
    print("=" * 70)
    pedido = pedido_in.a_entidad()
    print(pedido)
    for linea in pedido.lineas:
        print(" -", linea)

    print("\n" + "=" * 70)
    print("3) COMPARACIONES (dataclass order=True, compara por 'total')")
    print("=" * 70)
    otro_pedido = Pedido(
        id="PED-002",
        cliente="Adrian",
        lineas=[
            LineaPedido(
                producto=Producto(id="P3", nombre="Monitor", precio=Decimal("300")),
                cantidad=1,
            )
        ],
    )
    print("pedido:      ", pedido)
    print("otro_pedido: ", otro_pedido)
    print("pedido < otro_pedido ->", pedido < otro_pedido)
    print("pedido == otro_pedido ->", pedido == otro_pedido)

    print("\n" + "=" * 70)
    print("4) DUNDER __add__: combinar pedidos del mismo cliente")
    print("=" * 70)
    combinado = pedido + otro_pedido
    print(combinado)

    print("\n" + "=" * 70)
    print("5) SERIALIZACIÓN DE SALIDA (pydantic)")
    print("=" * 70)
    pedido_out = PedidoOut.desde_entidad(combinado)
    print("dict :", pedido_out.model_dump())
    print("json :", pedido_out.model_dump_json(indent=2))

    print("\n" + "=" * 70)
    print("6) VALIDACIÓN FALLIDA (esperada)")
    print("=" * 70)
    try:
        ProductoIn(id="PX", nombre="Malo", precio="-10")
    except Exception as e:
        print("Error capturado:", e)

    print("\n" + "=" * 70)
    print("7) VALIDACIÓN attrs (frozen + validator, esperada)")
    print("=" * 70)
    try:
        Producto(id="PY", nombre="Malo2", precio=Decimal("-5"))
    except Exception as e:
        print("Error capturado:", e)

    print("\nintentando actualizar un Producto frozen...")
    try:
        pedido.lineas[0].producto.precio = Decimal("999")
    except Exception as e:
        print("Error capturado:", e)
