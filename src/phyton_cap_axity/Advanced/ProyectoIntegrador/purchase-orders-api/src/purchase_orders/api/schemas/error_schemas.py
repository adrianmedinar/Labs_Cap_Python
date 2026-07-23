"""Schema Pydantic: forma estándar de respuesta de error de la API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(examples=["La orden de compra debe contener al menos un ítem."])
