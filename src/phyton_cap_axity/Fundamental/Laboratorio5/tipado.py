"""
========================================================================
Ejecutar directamente desde la terminal:

python -m mypy tipado.py

python -m pyright tipado.py

"""


from typing import Literal, Optional, Protocol, TypedDict, Union


# ----- TypedDict -----
class Usuario(TypedDict):
    id: int
    nombre: str
    activo: bool


def crear_usuario(u: Usuario) -> str:
    return f"Usuario {u['nombre']} (id={u['id']})"


# ----- Literal -----
Modo = Literal["dev", "test", "prod"]


def iniciar(modo: Modo) -> None:
    print(f"Iniciando en modo {modo}")


# ----- Protocol -----
class Dibujable(Protocol):
    def dibujar(self) -> str:
        ...


class Circulo:
    def dibujar(self) -> str:
        return "Dibujando un círculo"


class Cuadrado:
    def dibujar(self) -> str:
        return "Dibujando un cuadrado"


def renderizar(obj: Dibujable) -> None:
    print(obj.dibujar())


# ----- Union / Optional -----
def buscar_por_id(id: int) -> Optional[str]:
    if id == 1:
        return "Ana"
    return None


def procesar_valor(valor: Union[int, str]) -> str:
    return str(valor)


# ----- Uso correcto -----
usuario: Usuario = {"id": 1, "nombre": "Ana", "activo": True}
print(crear_usuario(usuario))

iniciar("dev")
renderizar(Circulo())
renderizar(Cuadrado())

resultado: Optional[str] = buscar_por_id(1)
print(procesar_valor(42))
print(procesar_valor("hola"))


# ----- ERRORES INTENCIONALES para el checker -----

# 1. Modo inválido (no está en el Literal)
# error: no es "dev" | "test" | "prod"
iniciar("staging")  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]

# 2. Falta una clave requerida en el TypedDict
usuario_incompleto: Usuario = {"id": 2, "nombre": "Luis"}  # error: falta "activo"

# 3. Tipo incorrecto en TypedDict
usuario_mal: Usuario = {"id": "3", "nombre": "Eva", "activo": True}  # error: id debe ser int

# 4. Objeto que no cumple el Protocol (falta el método dibujar)
class Triangulo:
    def pintar(self) -> str:
        return "Pintando triángulo"

renderizar(Triangulo())  # error: no tiene método dibujar()

# 5. Union mal usado
procesar_valor(3.14)  # error: float no es int ni str

# 6. Optional sin chequear antes de usar como str
def largo_nombre(id: int) -> int:
    nombre = buscar_por_id(id)
    return len(nombre)  # error: nombre puede ser None