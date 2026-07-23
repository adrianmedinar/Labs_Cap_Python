"""Fixtures compartidos para pruebas de integración, contrato y E2E.

Las pruebas UNITARIAS (dominio/aplicación) no necesitan nada de aquí:
usan objetos de dominio y fakes directamente. Este `conftest.py` provee
infraestructura real (BD SQLite en memoria, app FastAPI completa) para
las capas superiores de la pirámide de pruebas.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from purchase_orders.api.main import create_app
from purchase_orders.infrastructure.config import Settings
from purchase_orders.infrastructure.container import Container
from purchase_orders.infrastructure.db.base import Base


@pytest.fixture
def settings() -> Settings:
    """Settings de prueba: SQLite en memoria + secreto JWT fijo (>=32 chars)."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret_key="test-secret-key-for-tests-only-not-for-prod",
        jwt_access_token_expire_minutes=30,
        environment="test",
    )


@pytest_asyncio.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """Engine SQLite en memoria con el esquema completo ya creado."""
    from purchase_orders.infrastructure.db.base import create_engine

    eng = create_engine(settings.database_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    from purchase_orders.infrastructure.db.base import create_session_factory

    return create_session_factory(engine)


@pytest_asyncio.fixture
async def app(settings: Settings, engine: AsyncEngine):
    """App FastAPI completa, con el Container apuntando al engine de prueba
    (ya migrado) en lugar de crear uno nuevo en el lifespan por defecto.
    """
    application = create_app(settings)

    async with application.router.lifespan_context(application):
        # Sustituimos el engine que crea el Container por defecto (que
        # apunta a una BD *nueva* en memoria, vacía) por el que ya
        # preparamos con el esquema migrado en la fixture `engine`.
        container: Container = application.state.container
        await container.engine.dispose()
        container.engine = engine
        from purchase_orders.infrastructure.db.base import create_session_factory

        container.session_factory = create_session_factory(engine)
        yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers_factory(
    client: AsyncClient,
) -> Callable[..., AsyncIterator[dict[str, str]]]:
    """Fábrica: registra un usuario con el rol dado, hace login, y retorna
    los headers `Authorization: Bearer <token>` listos para usar.

    Uso:
        headers = await auth_headers_factory(role="approver_senior")
    """

    counter = {"n": 0}

    async def _make(
        role: str = "requester", username: str | None = None
    ) -> dict[str, str]:
        counter["n"] += 1
        username = username or f"user{counter['n']}"
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": f"{username}@corp.com",
                "password": "secret123",
                "role": role,
            },
        )
        response = await client.post(
            "/api/v1/auth/login", data={"username": username, "password": "secret123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
