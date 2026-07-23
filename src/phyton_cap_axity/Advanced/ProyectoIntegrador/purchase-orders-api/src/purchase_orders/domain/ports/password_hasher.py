"""Puerto (interfaz): PasswordHasher.

Abstrae el algoritmo de hashing de contraseñas (bcrypt, argon2, etc.) para
que la capa de aplicación pueda verificar/crear credenciales sin acoplarse
a una librería concreta.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Genera el hash de una contraseña en texto plano."""

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica que una contraseña en texto plano coincide con su hash."""
