"""
Engine y sesión async de SQLAlchemy.

`engine` y `AsyncSessionLocal` se construyen a partir de settings.DATABASE_URL,
lo que permite que los tests inyecten otra URL (SQLite en memoria) sin tocar
el resto de la app.
"""

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM."""

    pass


def make_engine(database_url: str | None = None):
    url = database_url or settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    return create_async_engine(url, echo=False, connect_args=connect_args)


engine = make_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncSession:
    """Dependency de FastAPI: entrega una sesión y la cierra al final del request."""
    async with AsyncSessionLocal() as session:
        yield session
