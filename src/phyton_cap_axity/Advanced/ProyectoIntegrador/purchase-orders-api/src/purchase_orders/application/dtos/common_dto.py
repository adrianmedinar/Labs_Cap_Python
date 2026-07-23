"""DTOs de la capa de aplicación para Proveedores y Autenticación."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateSupplierCommand:
    name: str
    tax_id: str
    email: str


@dataclass(frozen=True, slots=True)
class SupplierResult:
    id: UUID
    name: str
    tax_id: str
    email: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    username: str
    email: str
    password: str
    role: str


@dataclass(frozen=True, slots=True)
class UserResult:
    id: UUID
    username: str
    email: str
    role: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class LoginCommand:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class TokenResult:
    access_token: str
    token_type: str = "bearer"
