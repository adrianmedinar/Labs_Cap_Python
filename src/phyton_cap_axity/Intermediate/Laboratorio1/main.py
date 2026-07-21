"""
Demo end-to-end:
  1. Crea el esquema en SQLite en memoria.
  2. Ejercita CREATE, READ, UPDATE, DELETE sobre User, Order, OrderItem.

Base.metadata.create_all(), es
  la forma correcta de crear el esquema en un script/demo o en tests.

  Para ejecutar este script

  python main.py
"""

from decimal import Decimal

import crud
from database import SessionLocal, engine
from models import Base


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    # 1) Crear el esquema (tablas users, orders, order_items)
    Base.metadata.create_all(engine)

    session = SessionLocal()
    try:
        # ---------------- CREATE ----------------
        print_header("CREATE")
        user = crud.create_user(session, username="ammedina", email="amedina@axity.com")
        print("Usuario creado:", user)

        order = crud.create_order(session, user_id=user.id, status="pendiente")
        print("Orden creada:", order)

        item1 = crud.add_order_item(
            session,
            order_id=order.id,
            product_name="Teclado mecanico",
            quantity=1,
            unit_price=Decimal("899.00"),
        )
        item2 = crud.add_order_item(
            session,
            order_id=order.id,
            product_name="Mouse inalambrico",
            quantity=2,
            unit_price=Decimal("250.50"),
        )
        print("Items agregados:", item1, item2, sep="\n  ")

        # ---------------- READ ----------------
        print_header("READ")
        found_user = crud.get_user_by_username(session, "ana")
        print("Usuario encontrado por username:", found_user)

        orders = crud.list_orders_by_user(session, user.id)
        print(f"Ordenes del usuario {user.username}:", orders)

        total = crud.order_total(session, order.id)
        print(f"Total de la orden #{order.id}: ${total}")

        # ---------------- UPDATE ----------------
        print_header("UPDATE")
        crud.update_order_status(session, order.id, "pagado")
        updated_order = session.get(order.__class__, order.id)
        print("Orden tras actualizar status:", updated_order)

        crud.update_user_email(session, user.id, "adrian.medina@axity.com")
        print("Usuario tras actualizar email:", crud.get_user(session, user.id))

        # ---------------- DELETE ----------------
        print_header("DELETE")
        crud.delete_order_item(session, item2.id)
        print(
            f"Item {item2.id} eliminado. Total recalculado:",
            crud.order_total(session, order.id),
        )

        crud.delete_user(session, user.id)
        print("Usuario eliminado. Verificando cascade...")
        print("  Usuario:", crud.get_user(session, user.id))
        print(
            "  Ordenes restantes de ese usuario:",
            crud.list_orders_by_user(session, user.id),
        )

    finally:
        session.close()


if __name__ == "__main__":
    main()
