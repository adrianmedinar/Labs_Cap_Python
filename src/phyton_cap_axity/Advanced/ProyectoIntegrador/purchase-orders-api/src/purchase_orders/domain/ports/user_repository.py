"""Puerto (interfaz): UserRepository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from purchase_orders.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def add(self, user: User) -> None:
        """Persiste un nuevo usuario."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Recupera un usuario por su identificador."""

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        """Recupera un usuario por su nombre de usuario (para login)."""
