"""
CRUD.

SQLAlchemy 2.0 unifica Core y ORM: ambos estilos se ejecutan a traves
de session.execute(). Aqui se combinan a proposito:

  - Estilo ORM "clasico": session.add / session.get / session.delete,
    y navegacion por relaciones (order.items.append(...)).
  - Estilo SQLAlchemy Core: construcciones explicitas con
    insert() / select() / update() / delete(), que generan sentencias
    SQL de forma declarativa sin escribir SQL crudo.
"""

from decimal import Decimal
from typing import Optional, Sequence

from models import Order, OrderItem, User
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

# --------------------------------------------------------------------------
# CREATE
# --------------------------------------------------------------------------


def create_user(session: Session, username: str, email: str) -> User:
    """CREATE - estilo ORM."""
    user = User(username=username, email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_order(session: Session, user_id: int, status: str = "pendiente") -> Order:
    """CREATE - estilo SQLAlchemy Core (insert().returning())."""
    stmt = insert(Order).values(user_id=user_id, status=status).returning(Order.id)
    order_id = session.execute(stmt).scalar_one()
    session.commit()
    return session.get(Order, order_id)


def add_order_item(
    session: Session,
    order_id: int,
    product_name: str,
    quantity: int,
    unit_price: Decimal,
) -> OrderItem:
    """CREATE - estilo ORM, usando la relacion Order.items."""
    order = session.get(Order, order_id)
    if order is None:
        raise ValueError(f"Order {order_id} no existe")
    item = OrderItem(
        product_name=product_name, quantity=quantity, unit_price=unit_price
    )
    order.items.append(item)
    session.commit()
    session.refresh(item)
    return item


# --------------------------------------------------------------------------
# READ
# --------------------------------------------------------------------------


def get_user(session: Session, user_id: int) -> Optional[User]:
    """READ por clave primaria - estilo ORM."""
    return session.get(User, user_id)


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """READ - estilo SQLAlchemy Core (select() explicito)."""
    stmt = select(User).where(User.username == username)
    return session.execute(stmt).scalar_one_or_none()


def list_orders_by_user(session: Session, user_id: int) -> Sequence[Order]:
    """READ - estilo SQLAlchemy Core."""
    stmt = select(Order).where(Order.user_id == user_id)
    return session.execute(stmt).scalars().all()


def order_total(session: Session, order_id: int) -> Decimal:
    """READ agregando datos via relacion ORM."""
    order = session.get(Order, order_id)
    if order is None:
        return Decimal("0")
    return sum((item.subtotal for item in order.items), Decimal("0"))


# --------------------------------------------------------------------------
# UPDATE
# --------------------------------------------------------------------------


def update_order_status(session: Session, order_id: int, new_status: str) -> None:
    """UPDATE - estilo SQLAlchemy Core."""
    stmt = update(Order).where(Order.id == order_id).values(status=new_status)
    session.execute(stmt)
    session.commit()


def update_user_email(session: Session, user_id: int, new_email: str) -> None:
    """UPDATE - estilo ORM."""
    user = session.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} no existe")
    user.email = new_email
    session.commit()


# --------------------------------------------------------------------------
# DELETE
# --------------------------------------------------------------------------


def delete_order_item(session: Session, item_id: int) -> None:
    """DELETE - estilo SQLAlchemy Core."""
    stmt = delete(OrderItem).where(OrderItem.id == item_id)
    session.execute(stmt)
    session.commit()


def delete_user(session: Session, user_id: int) -> None:
    """DELETE - estilo ORM. Dispara cascade sobre Order y OrderItem."""
    user = session.get(User, user_id)
    if user is not None:
        session.delete(user)
        session.commit()
