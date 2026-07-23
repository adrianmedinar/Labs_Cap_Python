"""Adaptador: BcryptPasswordHasher.

Implementa el puerto `PasswordHasher` usando `passlib` con el esquema
bcrypt (estándar de la industria para hashing de contraseñas).
"""

from __future__ import annotations

from passlib.context import CryptContext

from purchase_orders.domain.ports.password_hasher import PasswordHasher

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return str(_pwd_context.hash(plain_password))

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bool(_pwd_context.verify(plain_password, hashed_password))
