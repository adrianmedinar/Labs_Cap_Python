from app.api.deps import get_current_active_user
from app.core.order_rules import can_transition
from app.crud import order as order_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.order import OrderCreate, OrderOut, OrderUpdate
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva orden",
)
async def create_order(
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await order_crud.create_order(db, order_in, owner_id=current_user.id)
    return order


@router.get(
    "",
    response_model=list[OrderOut],
    summary="Listar mis órdenes (paginado)",
)
async def read_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await order_crud.list_orders(
        db, owner_id=current_user.id, skip=skip, limit=limit
    )


@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="Obtener una orden por id",
    responses={404: {"description": "Orden no encontrada"}},
)
async def read_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await order_crud.get_order(db, order_id, owner_id=current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada"
        )
    return order


@router.patch(
    "/{order_id}",
    response_model=OrderOut,
    summary="Actualizar parcialmente una orden",
    responses={
        404: {"description": "Orden no encontrada"},
        409: {"description": "Transición de estado inválida"},
    },
)
async def update_order(
    order_id: int,
    order_in: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await order_crud.get_order(db, order_id, owner_id=current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada"
        )

    if order_in.status is not None and not can_transition(
        order.status, order_in.status
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transición inválida: {order.status.value} -> {order_in.status.value}",
        )

    return await order_crud.update_order(db, order, order_in)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una orden",
    responses={404: {"description": "Orden no encontrada"}},
)
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await order_crud.get_order(db, order_id, owner_id=current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada"
        )
    await order_crud.delete_order(db, order)
