"""Schemas Pydantic: Proveedores."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateSupplierRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Acme Corp"])
    tax_id: str = Field(min_length=1, max_length=50, examples=["RFC-ABC123456"])
    email: EmailStr = Field(examples=["ventas@acme.com"])


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tax_id: str
    email: str
    is_active: bool
