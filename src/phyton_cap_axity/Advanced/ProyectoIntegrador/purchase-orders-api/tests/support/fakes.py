"""Adaptadores *fake* en memoria: implementan los puertos del dominio sin
ninguna dependencia real (BD, JWT, bcrypt). Se usan en pruebas UNITARIAS de
la capa de aplicación, donde queremos verificar la orquestación de los
casos de uso sin pagar el costo (ni la fragilidad) de infraestructura real.

Las pruebas de INTEGRACIÓN, en cambio, sí usan los adaptadores reales
(SQLAlchemy contra SQLite/Postgres) — ver `tests/integration/`.
"""

from __future__ import annotations

from types import TracebackType
from uuid import UUID

from purchase_orders.domain.entities.purchase_order import PurchaseOrder
from purchase_orders.domain.entities.supplier import Supplier
from purchase_orders.domain.entities.user import User
from purchase_orders.domain.ports.password_hasher import PasswordHasher
from purchase_orders.domain.ports.purchase_order_repository import (
    PurchaseOrderRepository,
)
from purchase_orders.domain.ports.supplier_repository import SupplierRepository
from purchase_orders.domain.ports.token_provider import TokenPayload, TokenProvider
from purchase_orders.domain.ports.unit_of_work import UnitOfWork
from purchase_orders.domain.ports.user_repository import UserRepository


class FakePurchaseOrderRepository(PurchaseOrderRepository):
    def __init__(self) -> None:
        self._data: dict[UUID, PurchaseOrder] = {}

    async def add(self, order: PurchaseOrder) -> None:
        self._data[order.id] = order

    async def get_by_id(self, order_id: UUID) -> PurchaseOrder | None:
        return self._data.get(order_id)

    async def update(self, order: PurchaseOrder) -> None:
        self._data[order.id] = order

    async def list_by_status(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[PurchaseOrder]:
        values = list(self._data.values())
        if status:
            values = [o for o in values if o.status.value == status]
        return values[offset : offset + limit]

    async def list_by_supplier(
        self, supplier_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[PurchaseOrder]:
        values = [o for o in self._data.values() if o.supplier_id == supplier_id]
        return values[offset : offset + limit]


class FakeSupplierRepository(SupplierRepository):
    def __init__(self) -> None:
        self._data: dict[UUID, Supplier] = {}

    async def add(self, supplier: Supplier) -> None:
        self._data[supplier.id] = supplier

    async def get_by_id(self, supplier_id: UUID) -> Supplier | None:
        return self._data.get(supplier_id)

    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Supplier]:
        return [s for s in self._data.values() if s.is_active][offset : offset + limit]


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._data: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        self._data[user.id] = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._data.get(user_id)

    async def get_by_username(self, username: str) -> User | None:
        for user in self._data.values():
            if user.username == username:
                return user
        return None


class FakeUnitOfWork(UnitOfWork):
    """UoW fake: no hay transacción real, solo delega a los fakes en memoria."""

    def __init__(
        self,
        purchase_orders: FakePurchaseOrderRepository | None = None,
        suppliers: FakeSupplierRepository | None = None,
        users: FakeUserRepository | None = None,
    ) -> None:
        self.purchase_orders = purchase_orders or FakePurchaseOrderRepository()
        self.suppliers = suppliers or FakeSupplierRepository()
        self.users = users or FakeUserRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakePasswordHasher(PasswordHasher):
    """Hashing determinista (NO seguro) solo para pruebas: evita el costo
    real de bcrypt y hace las aserciones más simples de leer.
    """

    def hash(self, plain_password: str) -> str:
        return f"hashed:{plain_password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return hashed_password == f"hashed:{plain_password}"


class FakeTokenProvider(TokenProvider):
    def create_access_token(self, payload: TokenPayload) -> str:
        return f"fake-token:{payload.subject}:{payload.username}:{payload.role}"

    def decode(self, token: str) -> TokenPayload:
        _, subject, username, role = token.split(":")
        return TokenPayload(subject=UUID(subject), username=username, role=role)
