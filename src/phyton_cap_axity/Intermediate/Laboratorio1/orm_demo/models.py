"""
Entidades y relaciones del dominio.

Se definen con el ORM declarativo de SQLAlchemy 2.0 (Mapped /
mapped_column). Internamente, cada clase declarativa construye un
objeto de SQLAlchemy Core (sqlalchemy.Table) y todos esos objetos
quedan registrados en Base.metadata, que es exactamente el mismo
objeto MetaData que usa Alembic para autogenerar migraciones y el
mismo que se pasa a create_all()/drop_all().

Relaciones modeladas:
    User (1) ----< (N) Order (1) ----< (N) OrderItem
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Un usuario tiene muchas ordenes. cascade="all, delete-orphan":
    # si se borra el User, se borran tambien sus Order (y por cascada,
    # los OrderItem de esas ordenes).
    orders: Mapped[List["Order"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} email={self.email!r}>"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default="pendiente")

    user: Mapped["User"] = relationship(back_populates="orders")

    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} user_id={self.user_id} status={self.status!r}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity

    def __repr__(self) -> str:
        return (
            f"<OrderItem id={self.id} product={self.product_name!r} "
            f"qty={self.quantity} unit_price={self.unit_price}>"
        )
