"""Schemas Pydantic: Autenticación.

Estos modelos son el CONTRATO HTTP de la API (lo que ve el consumidor
externo). Son deliberadamente distintos de los DTOs de aplicación: los
schemas pertenecen a la capa API y pueden cambiar por razones de
presentación/versión de API sin tocar la capa de aplicación.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100, examples=["jane.doe"])
    email: EmailStr = Field(examples=["jane.doe@empresa.com"])
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(
        examples=["approver_senior"],
        description="Uno de: approver_junior, approver_senior, admin, requester",
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
