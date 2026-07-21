"""
retry_bacoff_gen_context.py
====================

Ejemplo completo que combina:
    - retry con backoff (decorador + closure + *args/**kwargs)
    - context manager de temporización (generador + @contextmanager)
    - generador por lotes (yield + iteradores)
    - logging con salida simultánea a consola y a archivo

------------------------------------------------------------------
EJECUCIÓN
------------------------------------------------------------------

1) Ejecutar directamente desde la terminal:

       python retry_backoff_gen_context.py

   Esto corre la simulación con 46 items de ejemplo, en lotes de 10,
   con un límite de tiempo total de 15 segundos. Verás el log en
   pantalla y, además, se escribirá en un archivo "proceso.log" en
   el mismo directorio (se agrega al final si el archivo ya existe).

2) Importarlo como módulo en otro script, en vez de ejecutarlo directo
   (el bloque 'if __name__ == "__main__":' evita que la simulación se
   dispare sola al importar):

       from retry_backoff_gen_context import procesar_datos

       resultados = procesar_datos(
           mis_datos_reales,
           tamaño_lote=50,
           tiempo_maximo=60,
       )
"""

import logging
import random
import time
from contextlib import contextmanager

# =====================================================================
# CONFIGURACIÓN DE LOGGING
# =====================================================================

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # cambia a logging.DEBUG para ver más detalle

_formato = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)

# Handler 1: consola (stderr) -> lo que ves en pantalla al ejecutar el script
_handler_consola = logging.StreamHandler()
_handler_consola.setFormatter(_formato)

# Handler 2: archivo -> queda un historial persistente en disco,
# útil para revisar corridas pasadas o depurar en producción
_handler_archivo = logging.FileHandler("proceso.log", mode="a", encoding="utf-8")
_handler_archivo.setFormatter(_formato)

logger.addHandler(_handler_consola)
logger.addHandler(_handler_archivo)


# =====================================================================
# 1) DECORADOR DE RETRY CON BACKOFF
#    Conceptos: decorador, closure, *args/**kwargs, funciones anidadas
# =====================================================================


def con_reintentos(intentos_max=4, espera_base=1):
    """
    Fábrica de decoradores: recibe CONFIGURACIÓN (intentos_max, espera_base)
    y devuelve el decorador real. Esto es lo que permite escribir
    @con_reintentos(intentos_max=5, espera_base=2) en vez de un decorador fijo.
    """

    def decorador(func):
        # 'func' queda "atrapada" aquí -> CLOSURE.
        # 'wrapper' recordará 'func', 'intentos_max' y 'espera_base'
        # aunque 'con_reintentos' ya haya terminado de ejecutarse.

        def wrapper(*args, **kwargs):
            # *args, **kwargs -> permiten que este wrapper sirva para
            # CUALQUIER función, sin importar qué argumentos reciba.
            for intento in range(intentos_max):
                try:
                    return func(*args, **kwargs)  # ejecuta la función original
                except Exception as e:
                    if intento == intentos_max - 1:
                        raise  # ya no quedan intentos: propaga el error real
                    espera = espera_base * (2**intento) + random.uniform(0, 0.5)
                    logger.warning(
                        "Falló %s (%s). Reintentando en %.2fs...",
                        func.__name__,
                        e,
                        espera,
                    )
                    time.sleep(espera)

        return wrapper

    return decorador


# =====================================================================
# 2) CONTEXT MANAGER DE TEMPORIZACIÓN
#    Conceptos: generador (yield), @contextmanager, lambda, try/finally
# =====================================================================


@contextmanager
def medir_tiempo(nombre="bloque"):
    """
    @contextmanager convierte un GENERADOR en un context manager:
    - todo lo antes del yield  -> se ejecuta al hacer 'with'
    - todo lo después (finally) -> se ejecuta al salir del 'with'
      (incluso si hubo una excepción dentro)
    """
    inicio = time.perf_counter()
    try:
        yield  # aquí se "pausa" y se ejecuta el bloque dentro del 'with'
    finally:
        duracion = time.perf_counter() - inicio
        logger.info("%s tardó %.2fs", nombre, duracion)


@contextmanager
def limite_de_tiempo(segundos):
    """
    Variante que expone una función para checar si ya se
    acabó el tiempo permitido.
    """
    inicio = time.monotonic()

    def sigue_en_tiempo():
        return (time.monotonic() - inicio) < segundos

    yield sigue_en_tiempo


# =====================================================================
# 3) GENERADOR POR LOTES
#    Conceptos: generador (yield), iterador, comprensión de listas
# =====================================================================


def por_lotes(iterable, tamaño):
    """
    GENERADOR: produce lotes uno a uno bajo demanda (yield), en vez de
    construir una lista con TODOS los lotes en memoria de una vez.

    """
    lote = []
    for item in iterable:
        lote.append(item)
        if len(lote) == tamaño:
            yield lote
            lote = []
    if lote:
        yield lote


# =====================================================================
# SIMULACIÓN: una "API" que falla de forma aleatoria
# =====================================================================


def api_enviar_lote_confalla(lote):
    if random.random() < 0.4:  # 40% de probabilidad de fallo
        raise ConnectionError("timeout simulado")
    return {"enviados": len(lote), "ids": [x for x in lote]}  # COMPRENSIÓN de lista


@con_reintentos(intentos_max=4, espera_base=0.5)
def enviar_lote(lote):
    return api_enviar_lote_confalla(lote)


# =====================================================================
# ORQUESTACIÓN: junta retry backoff, generador lotes y context manager
# =====================================================================


def procesar_datos(datos, tamaño_lote=10, tiempo_maximo=20):
    resultados = []

    with limite_de_tiempo(tiempo_maximo) as sigue_en_tiempo:
        with medir_tiempo("procesamiento completo"):

            for lote in por_lotes(datos, tamaño_lote):  # generador por lotes
                if not sigue_en_tiempo():  # lambda del context manager
                    logger.warning(
                        "Tiempo límite alcanzado, deteniendo el procesamiento."
                    )
                    break

                with medir_tiempo(f"lote de {len(lote)} items"):
                    try:
                        resultado = enviar_lote(lote)  # decorador con retry
                        resultados.append(resultado)
                    except Exception as e:
                        logger.error("Lote perdido definitivamente: %s", e)

    # COMPRENSIÓN: cuántos items se enviaron con éxito en total
    total_enviados = sum(r["enviados"] for r in resultados)
    logger.info("Total enviado con éxito: %d de %d", total_enviados, len(datos))
    return resultados


if __name__ == "__main__":
    datos = list(range(1, 47))  # 46 items de ejemplo
    procesar_datos(datos, tamaño_lote=10, tiempo_maximo=15)
