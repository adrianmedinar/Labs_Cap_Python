"""Schemas Pydantic: Órdenes de Compra."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LineItemRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=100, examples=["SKU-1234"])
    description: str = Field(min_length=1, max_length=500, examples=["Laptop Dell 14'"])
    quantity: int = Field(gt=0, examples=[2])
    unit_price: str = Field(
        examples=["1500.00"],
        description="Precio unitario como string decimal, ej. '1500.00'",
    )


class CreatePurchaseOrderRequest(BaseModel):
    supplier_id: UUID
    currency: str = Field(default="MXN", min_length=3, max_length=3)
    line_items: list[LineItemRequest] = Field(min_length=1)


class RejectPurchaseOrderRequest(BaseModel):
    reason: str = Field(
        min_length=1, max_length=500, examples=["Precio fuera de mercado"]
    )


class LineItemResponse(BaseModel):
    sku: str
    description: str
    quantity: int
    unit_price: str
    subtotal: str


class PurchaseOrderResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    status: str
    currency: str
    requested_by: str
    approved_by: str | None
    rejection_reason: str | None
    line_items: list[LineItemResponse]
    total: str
    created_at: datetime
    updated_at: datetime
    version: int
