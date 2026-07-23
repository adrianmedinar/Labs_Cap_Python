"""Router: Proveedores."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from purchase_orders.api.dependencies import CurrentUser, UnitOfWorkDep
from purchase_orders.api.schemas.error_schemas import ErrorResponse
from purchase_orders.api.schemas.supplier_schemas import (
    CreateSupplierRequest,
    SupplierResponse,
)
from purchase_orders.application.dtos.common_dto import CreateSupplierCommand
from purchase_orders.application.use_cases.create_supplier import (
    CreateSupplierUseCase,
)
from purchase_orders.application.use_cases.query_suppliers import (
    GetSupplierUseCase,
    ListSuppliersUseCase,
)

router = APIRouter(prefix="/api/v1/suppliers", tags=["Proveedores"])


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo proveedor",
)
async def create_supplier(
    payload: CreateSupplierRequest,
    uow: UnitOfWorkDep,
    _current_user: CurrentUser,
) -> SupplierResponse:
    use_case = CreateSupplierUseCase(uow)
    result = await use_case.execute(
        CreateSupplierCommand(
            name=payload.name, tax_id=payload.tax_id, email=payload.email
        )
    )
    return SupplierResponse.model_validate(result, from_attributes=True)


@router.get(
    "",
    response_model=list[SupplierResponse],
    summary="Listar proveedores activos",
)
async def list_suppliers(
    uow: UnitOfWorkDep,
    _current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SupplierResponse]:
    use_case = ListSuppliersUseCase(uow)
    results = await use_case.execute(limit=limit, offset=offset)
    return [SupplierResponse.model_validate(r, from_attributes=True) for r in results]


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Obtener un proveedor por ID",
    responses={404: {"model": ErrorResponse, "description": "Proveedor no encontrado"}},
)
async def get_supplier(
    supplier_id: UUID,
    uow: UnitOfWorkDep,
    _current_user: CurrentUser,
) -> SupplierResponse:
    use_case = GetSupplierUseCase(uow)
    result = await use_case.execute(supplier_id)
    return SupplierResponse.model_validate(result, from_attributes=True)
