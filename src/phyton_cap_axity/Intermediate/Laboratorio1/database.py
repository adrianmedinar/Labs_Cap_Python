"""
Configuracion de la base de datos.

Usamos SQLite EN MEMORIA (":memory:") para la demo. Por defecto, cada
conexion nueva a ':memory:' crea una base de datos DISTINTA y vacia,
lo cual rompe cualquier script que abra varias conexiones (por ejemplo
un Session por operacion). Para evitarlo usamos StaticPool, que le
indica a SQLAlchemy que reutilice SIEMPRE la misma conexion fisica
mientras el proceso este vivo.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = "sqlite:///:memory:"

# echo=True mostraria en consola cada sentencia SQL generada por
# SQLAlchemy Core, util para ver que hace el ORM "por debajo".
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
