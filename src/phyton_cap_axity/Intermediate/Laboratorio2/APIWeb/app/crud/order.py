from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.schemas.order import OrderCreate, OrderUpdate


async def create_order(db: AsyncSession, order_in: OrderCreate, owner_id: int) -> Order:
    order = Order(**order_in.model_dump(), owner_id=owner_id)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order(db: AsyncSession, order_id: int, owner_id: int) -> Order | None:
    """Solo devuelve la orden si pertenece al dueño (evita fugas entre usuarios)."""
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.owner_id == owner_id)
    )
    return result.scalar_one_or_none()


async def list_orders(db: AsyncSession, owner_id: int, skip: int = 0, limit: int = 100) -> list[Order]:
    result = await db.execute(
        select(Order).where(Order.owner_id == owner_id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def update_order(db: AsyncSession, order: Order, order_in: OrderUpdate) -> Order:
    update_data = order_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    await db.commit()
    await db.refresh(order)
    return order


async def delete_order(db: AsyncSession, order: Order) -> None:
    await db.delete(order)
    await db.commit()
