from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload de registro. EmailStr valida formato de correo automáticamente."""

    email: EmailStr = Field(..., examples=["ana@example.com"])
    password: str = Field(
        ..., min_length=8, max_length=128, examples=["SuperSecreta123"]
    )


class UserOut(BaseModel):
    """Lo que la API devuelve al cliente. Nunca incluye el hash de password."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime
