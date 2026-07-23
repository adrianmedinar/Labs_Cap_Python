"""Router: Órdenes de Compra.

Expone el ciclo de vida completo de la orden de compra como sub-recursos
de acción (`POST /{id}/submit`, `/approve`, etc.), siguiendo la convención
REST recomendada para transiciones de estado explícitas en vez de un
`PATCH` genérico que oculte las reglas de negocio.

Control de acceso por rol:
- Crear / consultar / enviar a proveedor / confirmar recepción / cerrar /
  cancelar: cualquier usuario autenticado.
- Aprobar / rechazar: exige un rol con permiso de aprobación
  (`approver_junior`, `approver_senior`, `admin`), y además el dominio
  valida el límite de monto autorizable para ese rol (`ApprovalPolicy`).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from purchase_orders.api.dependencies import CurrentUser, UnitOfWorkDep, require_roles
from purchase_orders.api.schemas.error_schemas import ErrorResponse
from purchase_orders.api.schemas.purchase_order_schemas import (
    CreatePurchaseOrderRequest,
    PurchaseOrderResponse,
    RejectPurchaseOrderRequest,
)
from purchase_orders.application.dtos.purchase_order_dto import (
    ApprovePurchaseOrderCommand,
    CreatePurchaseOrderCommand,
    LineItemCommand,
    RejectPurchaseOrderCommand,
)
from purchase_orders.application.use_cases.approve_purchase_order import (
    ApprovePurchaseOrderUseCase,
)
from purchase_orders.application.use_cases.create_purchase_order import (
    CreatePurchaseOrderUseCase,
)
from purchase_orders.application.use_cases.purchase_order_transitions import (
    CancelPurchaseOrderUseCase,
    ClosePurchaseOrderUseCase,
    ConfirmReceiptUseCase,
    SendToSupplierUseCase,
)
from purchase_orders.application.use_cases.query_purchase_orders import (
    GetPurchaseOrderUseCase,
    ListPurchaseOrdersUseCase,
)
from purchase_orders.application.use_cases.reject_purchase_order import (
    RejectPurchaseOrderUseCase,
)
from purchase_orders.application.use_cases.submit_purchase_order import (
    SubmitPurchaseOrderUseCase,
)

router = APIRouter(prefix="/api/v1/purchase-orders", tags=["Órdenes de Compra"])

_APPROVER_ROLES = ("approver_junior", "approver_senior", "admin")
ApproverUser = Annotated[CurrentUser, Depends(require_roles(*_APPROVER_ROLES))]


def _to_response(result: object) -> PurchaseOrderResponse:
    return PurchaseOrderResponse.model_validate(result, from_attributes=True)


@router.post(
    "",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva orden de compra (estado DRAFT)",
    responses={404: {"model": ErrorResponse, "description": "Proveedor no encontrado"}},
)
async def create_purchase_order(
    payload: CreatePurchaseOrderRequest,
    uow: UnitOfWorkDep,
    current_user: CurrentUser,
) -> PurchaseOrderResponse:
    command = CreatePurchaseOrderCommand(
        supplier_id=payload.supplier_id,
        requested_by=current_user.username,
        currency=payload.currency,
        line_items=[
            LineItemCommand(
                sku=li.sku,
                description=li.description,
                quantity=li.quantity,
                unit_price=li.unit_price,
            )
            for li in payload.line_items
        ],
    )
    result = await CreatePurchaseOrderUseCase(uow).execute(command)
    return _to_response(result)


@router.get(
    "",
    response_model=list[PurchaseOrderResponse],
    summary="Listar órdenes de compra (filtrable por estado o proveedor)",
)
async def list_purchase_orders(
    uow: UnitOfWorkDep,
    _current_user: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PurchaseOrderResponse]:
    results = await ListPurchaseOrdersUseCase(uow).execute(
        status=status_filter, supplier_id=supplier_id, limit=limit, offset=offset
    )
    return [_to_response(r) for r in results]


@router.get(
    "/{order_id}",
    response_model=PurchaseOrderResponse,
    summary="Obtener una orden de compra por ID",
    responses={404: {"model": ErrorResponse, "description": "Orden no encontrada"}},
)
async def get_purchase_order(
    order_id: UUID, uow: UnitOfWorkDep, _current_user: CurrentUser
) -> PurchaseOrderResponse:
    result = await GetPurchaseOrderUseCase(uow).execute(order_id)
    return _to_response(result)


@router.post(
    "/{order_id}/submit",
    response_model=PurchaseOrderResponse,
    summary="Enviar la orden a aprobación (DRAFT → PENDING_APPROVAL)",
    responses={
        409: {"model": ErrorResponse, "description": "Transición de estado inválida"}
    },
)
async def submit_purchase_order(
    order_id: UUID, uow: UnitOfWorkDep, _current_user: CurrentUser
) -> PurchaseOrderResponse:
    result = await SubmitPurchaseOrderUseCase(uow).execute(order_id)
    return _to_response(result)


@router.post(
    "/{order_id}/approve",
    response_model=PurchaseOrderResponse,
    summary="Aprobar la orden (PENDING_APPROVAL → APPROVED)",
    description="Requiere un rol con permiso de aprobación y está sujeto al "
    "límite de monto autorizable de ese rol (`ApprovalPolicy`).",
    responses={
        403: {
            "model": ErrorResponse,
            "description": "Rol sin permiso o monto excede el límite",
        },
        409: {"model": ErrorResponse, "description": "Transición de estado inválida"},
    },
)
async def approve_purchase_order(
    order_id: UUID, uow: UnitOfWorkDep, approver: ApproverUser
) -> PurchaseOrderResponse:
    command = ApprovePurchaseOrderCommand(
        order_id=order_id, approved_by=approver.username, approver_role=approver.role
    )
    result = await ApprovePurchaseOrderUseCase(uow).execute(command)
    return _to_response(result)


@router.post(
    "/{order_id}/reject",
    response_model=PurchaseOrderResponse,
    summary="Rechazar la orden (PENDING_APPROVAL → REJECTED)",
    responses={
        403: {"model": ErrorResponse, "description": "Rol sin permiso de aprobación"},
        409: {"model": ErrorResponse, "description": "Transición de estado inválida"},
    },
)
async def reject_purchase_order(
    order_id: UUID,
    payload: RejectPurchaseOrderRequest,
    uow: UnitOfWorkDep,
    _approver: ApproverUser,
) -> PurchaseOrderResponse:
    command = RejectPurchaseOrderCommand(order_id=order_id, reason=payload.reason)
    result = await RejectPurchaseOrderUseCase(uow).execute(command)
    return _to_response(result)


@router.post(
    "/{order_id}/send-to-supplier",
    response_model=PurchaseOrderResponse,
    summary="Enviar la orden al proveedor (APPROVED → SENT_TO_SUPPLIER)",
    responses={
        409: {"model": ErrorResponse, "description": "Transición de estado inválida"}
    },
)
async def send_to_supplier(
    order_id: UUID, uow: UnitOfWorkDep, _current_user: CurrentUser
) -> PurchaseOrderResponse:
    result = await SendToSupplierUseCase(uow).execute(order_id)
    return _to_response(result)


@router.post(
    "/{order_id}/confirm-receipt",
    response_model=PurchaseOrderResponse,
    summary="Confirmar recepción de la orden (SENT_TO_SUPPLIER → RECEIVED)",
    responses={
        409: {"model": ErrorResponse, "description": "Transición de estado inválida"}
    },
)
async def confirm_receipt(
    order_id: UUID, uow: UnitOfWorkDep, _current_user: CurrentUser
) -> PurchaseOrderResponse:
    result = await ConfirmReceiptUseCase(uow).execute(order_id)
    return _to_response(result)


@router.post(
    "/{order_id}/close",
    response_model=PurchaseOrderResponse,
    summary="Cerrar la orden (RECEIVED → CLOSED)",
    responses={
        409: {"model": ErrorResponse, "description": "Transición de estado inválida"}
    },
)
async def close_purchase_order(
    order_id: UUID, uow: UnitOfWorkDep, _current_user: CurrentUser
) -> PurchaseOrderResponse:
    result = await ClosePurchaseOrderUseCase(uow).execute(order_id)
    return _to_response(result)


@router.post(
    "/{order_id}/cancel",
    response_model=PurchaseOrderResponse,
    summary="Cancelar la orden (DRAFT/PENDING_APPROVAL/APPROVED → CANCELLED)",
    responses={
        409: {"model": ErrorResponse, "description": "Transición de estado inválida"}
    },
)
async def cancel_purchase_order(
    order_id: UUID, uow: UnitOfWorkDep, _current_user: CurrentUser
) -> PurchaseOrderResponse:
    result = await CancelPurchaseOrderUseCase(uow).execute(order_id)
    return _to_response(result)
