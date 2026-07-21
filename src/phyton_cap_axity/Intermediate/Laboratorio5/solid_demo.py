import sqlite3
import unittest
from typing import Optional, Protocol, TypedDict

# ==============================================================================
# 1. PUERTO Y DTO (Contrato de Dominio)
# ==============================================================================


class UserData(TypedDict):
    id: str
    name: str


class UserRepository(Protocol):
    """
    Puerto (interfaz) que define las operaciones que el dominio requiere
    para manejar el persistimiento de usuarios.
    """

    def save(self, user_id: str, name: str) -> None: ...

    def get_by_id(self, user_id: str) -> Optional[UserData]: ...


# ==============================================================================
# 2. ADAPTADORES (Implementaciones Concretas)
# ==============================================================================


class InMemoryUserRepository:
    """Adaptador de almacenamiento temporal en memoria (RAM)."""

    def __init__(self) -> None:
        self._storage: dict[str, UserData] = {}

    def save(self, user_id: str, name: str) -> None:
        self._storage[user_id] = {"id": user_id, "name": name}

    def get_by_id(self, user_id: str) -> Optional[UserData]:
        return self._storage.get(user_id)


class SQLiteUserRepository:
    """Adaptador de almacenamiento persistente usando SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.conn = connection
        self._create_schema()

    def _create_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT)"
            )

    def save(self, user_id: str, name: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO users (id, name) VALUES (?, ?)",
                (user_id, name),
            )

    def get_by_id(self, user_id: str) -> Optional[UserData]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1]}


# ==============================================================================
# 3. SERVICIO DE DOMINIO (Depende únicamente de la abstracción)
# ==============================================================================


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        # Inyección de dependencias mediante la interfaz del puerto
        self.repository = repository

    def register_user(self, user_id: str, name: str) -> UserData:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("El nombre no puede estar vacío.")

        self.repository.save(user_id, clean_name)
        user = self.repository.get_by_id(user_id)

        if user is None:
            raise RuntimeError("Error al recuperar el usuario registrado.")

        return user


# ==============================================================================
# 4. VERIFICACIÓN DE LISKOV (Contract Testing con unittest)
# ==============================================================================


class UserRepositoryContractMixin:
    """
    Suite de pruebas de contrato.
    Cualquier clase que implemente UserRepository DEBE pasar estas pruebas.
    Garantiza el cumplimiento del principio LSP (Sustitución de Liskov).
    """

    def get_repository(self) -> UserRepository:
        raise NotImplementedError

    def test_save_and_retrieve_user(self):
        repo = self.get_repository()
        repo.save("usr-100", "Ana Garcia")
        user = repo.get_by_id("usr-100")

        self.assertEqual(user, {"id": "usr-100", "name": "Ana Garcia"})

    def test_get_non_existent_user_returns_none(self):
        repo = self.get_repository()
        user = repo.get_by_id("usr-non-existent")
        self.assertIsNone(user)

    def test_overwrite_existing_user(self):
        repo = self.get_repository()
        repo.save("usr-100", "Ana")
        repo.save("usr-100", "Ana Maria")

        user = repo.get_by_id("usr-100")
        self.assertEqual(user, {"id": "usr-100", "name": "Ana Maria"})


class TestInMemoryUserRepository(unittest.TestCase, UserRepositoryContractMixin):
    def get_repository(self) -> UserRepository:
        return InMemoryUserRepository()


class TestSQLiteUserRepository(unittest.TestCase, UserRepositoryContractMixin):
    def get_repository(self) -> UserRepository:
        # Usamos una base de datos SQLite efímera en memoria para la prueba
        conn = sqlite3.connect(":memory:")
        return SQLiteUserRepository(conn)


# ==============================================================================
# 5. DEMOSTRACIÓN DE EJECUCIÓN
# ==============================================================================


def run_demo():
    print("=" * 60)
    print("DEMO: Intercambiabilidad de repositorios en UserService")
    print("=" * 60)

    # 1. Usando el adaptador en memoria
    mem_repo = InMemoryUserRepository()
    service_mem = UserService(repository=mem_repo)
    user_mem = service_mem.register_user("u1", "  Carlos Mendoza  ")
    print(f"[In-Memory] Usuario creado con éxito: {user_mem}")

    # 2. Usando el adaptador SQLite sin modificar ni una sola línea de UserService
    sqlite_conn = sqlite3.connect(":memory:")
    sql_repo = SQLiteUserRepository(sqlite_conn)
    service_sql = UserService(repository=sql_repo)
    user_sql = service_sql.register_user("u2", "  Lucía Fernández  ")
    print(f"[SQLite]    Usuario creado con éxito: {user_sql}")

    print("\n" + "=" * 60)
    print("EJECUTANDO CONTRACT TESTS (LSP Verification)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Mostrar demo de uso
    run_demo()

    # Ejecutar suite de pruebas de contrato
    unittest.main(verbosity=2)
