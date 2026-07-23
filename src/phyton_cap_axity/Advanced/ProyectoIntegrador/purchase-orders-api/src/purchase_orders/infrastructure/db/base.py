"""Base declarativa y factoría de engine/sesión asíncrona de SQLAlchemy.

Este módulo es puramente de infraestructura: el dominio y la aplicación
jamás importan nada de aquí directamente.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM."""


def create_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    if database_url.startswith("sqlite"):
        # StaticPool: una única conexión compartida por todas las sesiones.
        # Imprescindible para `sqlite+aiosqlite:///:memory:`, donde cada
        # conexión nueva vería una base de datos vacía distinta.
        return create_async_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_async_engine(database_url, echo=echo)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
