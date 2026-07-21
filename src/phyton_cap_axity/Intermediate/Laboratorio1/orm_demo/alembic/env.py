"""
env.py de Alembic.

Importa Base.metadata desde models.py para que:
  - 'alembic revision --autogenerate' pueda comparar el estado de la
    BD contra los modelos y generar el diff automaticamente.
  - 'alembic upgrade/downgrade' sepan que metadata usar.
"""

import os

# Permite 'import models' al correr alembic desde la raiz del proyecto
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.append(os.getcwd())

from models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# metadata objetivo para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera SQL sin conectarse a la BD ('alembic upgrade --sql')."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta las migraciones conectandose de verdad a la BD."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
