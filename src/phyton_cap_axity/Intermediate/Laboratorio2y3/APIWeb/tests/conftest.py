"""
Fixtures compartidas para los tests de integración.

Estrategia de DB temporal:
- Se crea un engine SQLite in-memory distinto POR TEST (StaticPool para que
  todas las conexiones de ese engine compartan la misma DB en memoria).
- Se sobreescribe la dependency `get_db` de la app para que use esa sesión.
- Al terminar el test se descarta el engine -> la DB desaparece sola.

"""

import pytest
import pytest_asyncio
from app.api.deps import get_db
from app.db.session import Base
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest_asyncio.fixture
async def db_session():
    """Crea una DB SQLite en memoria fresca para cada test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )

    async with TestingSessionLocal() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Cliente HTTP async con la dependency get_db sobreescrita hacia la DB temporal."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user_token(client):
    """Registra un usuario y devuelve su JWT, listo para usar en Authorization header."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "amedina@axity.net", "password": "Clav3$egur@123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "amedina@axity.net", "password": "Clav3$egur@123"},
    )
    token = resp.json()["access_token"]
    return token


@pytest.fixture
def auth_headers(registered_user_token):
    return {"Authorization": f"Bearer {registered_user_token}"}
