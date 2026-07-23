"""Entidad: User.

Representa a un usuario del sistema con un rol de negocio. El rol es lo
que consume `ApprovalPolicy` para decidir límites de aprobación. La
contraseña se almacena siempre como hash (nunca en texto plano); el hashing
en sí es responsabilidad de un adaptador de infraestructura a través del
puerto `PasswordHasher`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class User:
    username: str
    email: str
    hashed_password: str
    role: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
