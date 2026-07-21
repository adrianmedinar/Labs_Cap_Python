from datetime import datetime

from app.models.order import OrderStatus
from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderBase(BaseModel):
    item: str = Field(..., min_length=1, max_length=255, examples=["Teclado mecánico"])
    quantity: int = Field(
        ..., gt=0, le=10_000, description="Cantidad de unidades, debe ser > 0"
    )
    unit_price: float = Field(..., gt=0, description="Precio unitario, debe ser > 0")

    @field_validator("item")
    @classmethod
    def item_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre del artículo no puede estar vacío")
        return v


class OrderCreate(OrderBase):
    """Payload para crear una orden. El status inicial siempre es 'pending'."""

    pass


class OrderUpdate(BaseModel):
    """Payload para actualizar una orden. Todos los campos son opcionales (PATCH)."""

    item: str | None = Field(None, min_length=1, max_length=255)
    quantity: int | None = Field(None, gt=0, le=10_000)
    unit_price: float | None = Field(None, gt=0)
    status: OrderStatus | None = None


class OrderOut(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    owner_id: int
    created_at: datetime
    total_price: float
