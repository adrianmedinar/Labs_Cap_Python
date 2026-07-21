#!/usr/bin/env python3
"""
procesar_json.py
-----------------
Lee un archivo JSON, valida y filtra sus registros, y genera agregaciones
por categoría.

Sigue el espíritu de PEP 20 (Zen de Python):
- Explícito es mejor que implícito.
- Simple es mejor que complejo.
- Los errores nunca deberían pasar silenciosamente.
- Ante la ambigüedad, evita la tentación de adivinar.

Uso:
    python procesar_json.py datos.json -o salida.json
    python procesar_json.py datos_validos.json -o salida.json
    python procesar_json.py datos_validos.json -c ventas -m 100 -a promedio -o salida.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Alias de tipos (sintaxis `type` introducida en Python 3.12 / PEP 695)
# --------------------------------------------------------------------------
type Registro = dict[str, Any]
type Registros = list[Registro]

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Expresiones regulares reutilizables
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUMERO_RE = re.compile(r"-?\d+(?:\.\d+)?")


# --------------------------------------------------------------------------
# Excepciones propias
# --------------------------------------------------------------------------
class ProcesamientoJSONError(Exception):
    """Excepción base para errores de este script."""


class ArchivoJSONError(ProcesamientoJSONError):
    """Error relacionado con la lectura/escritura del archivo en disco."""


class FormatoInvalidoError(ProcesamientoJSONError):
    """Error relacionado con la estructura general del JSON."""


class RegistroInvalidoError(ProcesamientoJSONError):
    """Un registro individual no cumple con el esquema esperado."""

    def __init__(self, indice: int, motivo: str) -> None:
        self.indice = indice
        self.motivo = motivo
        super().__init__(f"Registro #{indice}: {motivo}")


# --------------------------------------------------------------------------
# Carga del archivo JSON
# --------------------------------------------------------------------------
def cargar_json(ruta: Path) -> Registros:
    """Lee y parsea un archivo JSON, manejando los errores comunes de E/S."""
    try:
        contenido = ruta.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ArchivoJSONError(f"No se encontró el archivo: {ruta}") from exc
    except PermissionError as exc:
        raise ArchivoJSONError(f"Sin permisos para leer: {ruta}") from exc
    except IsADirectoryError as exc:
        raise ArchivoJSONError(
            f"La ruta es un directorio, no un archivo: {ruta}"
        ) from exc
    except OSError as exc:
        raise ArchivoJSONError(f"Error de E/S al leer {ruta}: {exc}") from exc

    if not contenido.strip():
        raise FormatoInvalidoError(f"El archivo {ruta} está vacío")

    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError as exc:
        raise FormatoInvalidoError(
            f"JSON inválido en {ruta} (línea {exc.lineno}, columna {exc.colno}): {exc.msg}"
        ) from exc

    match datos:
        case list() as registros:
            return registros
        case dict() as registro_unico:
            # Se acepta también un único objeto en la raíz en vez de una lista.
            return [registro_unico]
        case _:
            raise FormatoInvalidoError(
                "Se esperaba una lista de objetos o un objeto JSON en la raíz"
            )


# --------------------------------------------------------------------------
# Validación de cada registro (pattern matching + regex)
# --------------------------------------------------------------------------
def validar_registro(indice: int, registro: Any) -> Registro:
    """Valida la forma y el contenido de un registro individual.

    Esquema esperado: {"categoria": str, "monto": number|str, ...opcionales}
    """
    match registro:
        case {"categoria": str(cat), "monto": (int() | float()) as monto, **resto}:
            if monto < 0:
                raise RegistroInvalidoError(indice, "el monto no puede ser negativo")

            if (email := resto.get("email")) is not None and not EMAIL_RE.match(email):
                raise RegistroInvalidoError(indice, f"email inválido: {email!r}")

            if (fecha := resto.get("fecha")) is not None and not FECHA_RE.match(fecha):
                raise RegistroInvalidoError(
                    indice, f"fecha inválida (se espera YYYY-MM-DD): {fecha!r}"
                )

            return {"categoria": cat, "monto": float(monto), **resto}

        case {"categoria": str(cat), "monto": str(monto_txt), **resto}:
            # Se intenta extraer un número desde textos tipo "150.5 USD".
            if not (coincidencia := NUMERO_RE.search(monto_txt)):
                raise RegistroInvalidoError(
                    indice, f"no se pudo extraer un número de: {monto_txt!r}"
                )
            return {"categoria": cat, "monto": float(coincidencia.group()), **resto}

        case {"categoria": _, "monto": _}:
            raise RegistroInvalidoError(indice, "tipo de 'monto' no soportado")

        case dict():
            raise RegistroInvalidoError(indice, "faltan campos 'categoria' y/o 'monto'")

        case _:
            raise RegistroInvalidoError(indice, "el registro no es un objeto JSON")


def validar_registros(registros: Registros) -> Registros:
    """Valida todos los registros, acumulando errores en un grupo de excepciones."""
    validos: Registros = []
    errores: list[RegistroInvalidoError] = []

    for indice, registro in enumerate(registros):
        try:
            validos.append(validar_registro(indice, registro))
        except RegistroInvalidoError as exc:
            errores.append(exc)

    if errores:
        # Exception Groups (PEP 654, disponible desde Python 3.11).
        raise ExceptionGroup(
            f"{len(errores)} registro(s) inválido(s) de {len(registros)}", errores
        )

    return validos


# --------------------------------------------------------------------------
# Filtrado
# --------------------------------------------------------------------------
def filtrar_registros(
    registros: Registros,
    categoria: str | None = None,
    monto_minimo: float | None = None,
) -> Registros:
    """Filtra registros por categoría exacta y/o monto mínimo."""
    resultado = registros

    if categoria is not None:
        resultado = [r for r in resultado if r["categoria"] == categoria]

    if monto_minimo is not None:
        resultado = [r for r in resultado if r["monto"] >= monto_minimo]

    return resultado


# --------------------------------------------------------------------------
# Agregación (pattern matching para elegir la operación)
# --------------------------------------------------------------------------
def agregar_por_categoria(registros: Registros, operacion: str) -> dict[str, float]:
    """Agrupa los registros por categoría y aplica la operación solicitada."""
    grupos: dict[str, list[float]] = {}
    for registro in registros:
        grupos.setdefault(registro["categoria"], []).append(registro["monto"])

    resultado: dict[str, float] = {}
    for categoria, montos in grupos.items():
        match operacion:
            case "suma":
                resultado[categoria] = sum(montos)
            case "promedio":
                resultado[categoria] = sum(montos) / len(montos)
            case "conteo":
                resultado[categoria] = len(montos)
            case "maximo":
                resultado[categoria] = max(montos)
            case "minimo":
                resultado[categoria] = min(montos)
            case _:
                raise ValueError(f"Operación de agregación no soportada: {operacion!r}")

    return resultado


# --------------------------------------------------------------------------
# Guardado del resultado
# --------------------------------------------------------------------------
def guardar_json(datos: Any, ruta: Path) -> None:
    """Guarda datos en un archivo JSON, manejando errores de escritura."""
    try:
        ruta.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        raise ArchivoJSONError(f"No se pudo escribir en {ruta}: {exc}") from exc


# --------------------------------------------------------------------------
# Parametros del programa
# --------------------------------------------------------------------------
def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lee, filtra y agrega datos de un archivo JSON."
    )
    parser.add_argument("entrada", type=Path, help="Ruta del archivo JSON de entrada")
    parser.add_argument(
        "-o",
        "--salida",
        type=Path,
        default=None,
        help="Ruta del archivo JSON de salida (por defecto: se imprime en pantalla)",
    )
    parser.add_argument(
        "-c", "--categoria", type=str, default=None, help="Filtrar por categoría exacta"
    )
    parser.add_argument(
        "-m",
        "--monto-minimo",
        type=float,
        default=None,
        help="Filtrar por monto mínimo",
    )
    parser.add_argument(
        "-a",
        "--agregacion",
        type=str,
        default="suma",
        choices=["suma", "promedio", "conteo", "maximo", "minimo"],
        help="Operación de agregación por categoría (por defecto: suma)",
    )
    return parser


def main() -> int:
    parser = crear_parser()
    args = parser.parse_args()

    try:
        registros_crudos = cargar_json(args.entrada)
        registros = validar_registros(registros_crudos)

        registros_filtrados = filtrar_registros(
            registros, categoria=args.categoria, monto_minimo=args.monto_minimo
        )

        if not registros_filtrados:
            logger.warning("El filtro aplicado no arrojó ningún registro")

        agregados = agregar_por_categoria(registros_filtrados, args.agregacion)

        resultado = {
            "total_registros": len(registros_filtrados),
            "agregacion": args.agregacion,
            "resultados_por_categoria": agregados,
            "registros": registros_filtrados,
        }

        if args.salida:
            guardar_json(resultado, args.salida)
            logger.info("Resultado guardado en %s", args.salida)
        else:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))

        return 0

    except ExceptionGroup as eg:
        logger.error("Se encontraron errores de validación:")
        for err in eg.exceptions:
            logger.error("  - %s", err)
        return 1

    except ArchivoJSONError as exc:
        logger.error("Error de archivo: %s", exc)
        return 1

    except FormatoInvalidoError as exc:
        logger.error("Error de formato: %s", exc)
        return 1

    except ProcesamientoJSONError as exc:
        logger.error("Error de procesamiento: %s", exc)
        return 1

    except Exception as exc:  # último recurso: nunca callar errores silenciosamente
        logger.exception("Error inesperado: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
