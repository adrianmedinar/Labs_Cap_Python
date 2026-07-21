"""
Demo de concurrencia y paralelismo en Python
=============================================

Este script compara distintas estrategias para trabajo I/O-bound y CPU-bound,
e incluye mediciones con timeit/cProfile.

Conceptos cubiertos (ver docstrings de cada sección):
  1. GIL (Global Interpreter Lock) y sus implicaciones
  2. threading + concurrent.futures (I/O-bound)
  3. asyncio: event loop, async/await, semáforos
  4. multiprocessing / ProcessPoolExecutor (CPU-bound)
  5. Medición con timeit y cProfile

Tipo de Trabajo	Estrategia Recomendada	¿Por qué?
I/O-Bound (Red, Web Scraping, APIs)	asyncio	Escala a miles de conexiones concurrentes con bajísimo consumo de recursos.
I/O-Bound (Pocas tareas o código heredado)	threading	Fácil de implementar sin tener que reescribir código a async/await.
CPU-Bound (Matemáticas, imágenes, IA)	multiprocessing	Supera la barrera del GIL aprovechando múltiples núcleos de la CPU.
Secuencial / Simple	Código estándar	Evita la complejidad de la concurrencia si el volumen de datos es pequeño.


"""

from __future__ import annotations

import asyncio
import cProfile
import io
import pstats
import threading
import time
import timeit
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

# ---------------------------------------------------------------------------
# 0. Servidor local de prueba (simula un endpoint remoto con latencia)
# ---------------------------------------------------------------------------

LATENCY_S = 0.2  # latencia simulada por request (I/O wait)
N_REQUESTS = 20  # número de "requests" a realizar
PORT = 8765


class SlowHandler(BaseHTTPRequestHandler):
    """Handler que duerme LATENCY_S antes de responder, simulando red lenta."""

    def do_GET(self):
        time.sleep(LATENCY_S)  # <-- espera de I/O (libera el GIL)
        body = b'{"status": "ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # silenciar logs del servidor


def start_test_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), SlowHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


URLS = [f"http://127.0.0.1:{PORT}/item/{i}" for i in range(N_REQUESTS)]


# ---------------------------------------------------------------------------
# 1. GIL (Global Interpreter Lock)
# ---------------------------------------------------------------------------
"""
El GIL es un mutex global del intérprete CPython que garantiza que, en un
proceso, solo un hilo ejecute bytecode Python a la vez.

Implicaciones prácticas:
  - Para código CPU-bound puro en Python, usar varios *threads* NO acelera
    el trabajo: siguen turnándose el GIL, así que el tiempo total es similar
    que con un solo hilo.
  - Para código I/O-bound (esperar red, disco, sockets), el GIL SÍ se libera
    mientras el hilo está bloqueado en la llamada de I/O (p. ej. socket.recv,
    time.sleep libera el GIL a nivel C). Por eso threading SÍ ayuda aquí:
    mientras un hilo espera la respuesta de la red, otro puede ejecutar
    Python.
  - Para acelerar CPU-bound de verdad, hace falta *multiprocessing*: cada
    proceso tiene su propio intérprete y su propio GIL, así que sí hay
    paralelismo real entre núcleos.
"""


# ---------------------------------------------------------------------------
# 2. Versión SÍNCRONA (baseline) — un request detrás de otro
# ---------------------------------------------------------------------------


def fetch_sync_one(client: httpx.Client, url: str) -> int:
    resp = client.get(url)
    return resp.status_code


def fetch_all_sync(urls: list[str]) -> list[int]:
    """Baseline secuencial: N requests, uno tras otro. Tiempo ~ N * latencia."""
    with httpx.Client(timeout=10.0) as client:
        return [fetch_sync_one(client, u) for u in urls]


# ---------------------------------------------------------------------------
# 3. threading + concurrent.futures (I/O-bound, se beneficia de la liberación
#    del GIL durante la espera de red)
# ---------------------------------------------------------------------------


def fetch_all_threads(urls: list[str], max_workers: int = 10) -> list[int]:
    """
    ThreadPoolExecutor lanza un pool de hilos de SO reales. Cada hilo hace
    una llamada bloqueante (httpx.Client.get). Mientras un hilo espera la
    respuesta del socket, el GIL queda libre y otro hilo puede avanzar.
    Resultado: el tiempo total se acerca a latencia * N / max_workers en
    lugar de latencia * N.
    """
    results = []
    with httpx.Client(timeout=10.0) as client:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(fetch_sync_one, client, u) for u in urls]
            for fut in as_completed(futures):
                results.append(fut.result())
    return results


# ---------------------------------------------------------------------------
# 4. asyncio: event loop, async/await, semáforo para limitar concurrencia
# ---------------------------------------------------------------------------
"""
asyncio implementa concurrencia cooperativa dentro de UN solo hilo mediante
un *event loop*: un bucle que va despachando corrutinas y, cuando una hace
`await` sobre una operación de I/O (como un request HTTP), cede el control
para que el loop ejecute otras corrutinas mientras la primera espera.

"""


async def fetch_async_one(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str
) -> int:
    async with sem:  # adquiere un "cupo" del semáforo
        resp = await client.get(url)  # await: cede el control al event loop
        return resp.status_code


async def fetch_all_async(urls: list[str], max_concurrency: int = 10) -> list[int]:
    sem = asyncio.Semaphore(max_concurrency)
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [fetch_async_one(client, sem, u) for u in urls]
        return await asyncio.gather(*tasks)


def run_async_fetch(urls: list[str], max_concurrency: int = 10) -> list[int]:
    """Punto de entrada síncrono que arranca el event loop de asyncio."""
    return asyncio.run(fetch_all_async(urls, max_concurrency))


# ---------------------------------------------------------------------------
# 5. multiprocessing / ProcessPoolExecutor para trabajo CPU-bound
# ---------------------------------------------------------------------------
"""
multiprocessing crea procesos de SO independientes, cada uno con su propio
intérprete Python y su propio GIL. Por eso, a diferencia de threading, SÍ
logra paralelismo real en tareas que consumen CPU (cálculos numéricos,
compresión, procesamiento de imágenes, etc.), aprovechando varios núcleos.

"""


def es_primo(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def contar_primos(rango: tuple[int, int]) -> int:
    """Función CPU-bound: cuenta primos en [inicio, fin). Trabajo pesado de CPU."""
    inicio, fin = rango
    return sum(1 for n in range(inicio, fin) if es_primo(n))


NUMEROS_A_PROBAR = 200_000  # tamaño del rango total a analizar
N_CHUNKS = 8  # en cuántos trozos se divide el trabajo


def partir_rango(total: int, n_chunks: int) -> list[tuple[int, int]]:
    paso = total // n_chunks
    limites = [(i * paso, (i + 1) * paso) for i in range(n_chunks)]
    limites[-1] = (limites[-1][0], total)  # el último trozo se lleva el resto
    return limites


def contar_primos_secuencial(total: int) -> int:
    return contar_primos((0, total))


def contar_primos_threads(total: int, n_chunks: int = N_CHUNKS) -> int:
    """Mismo trabajo repartido en threads: NO acelera por culpa del GIL."""
    chunks = partir_rango(total, n_chunks)
    with ThreadPoolExecutor(max_workers=n_chunks) as pool:
        return sum(pool.map(contar_primos, chunks))


def contar_primos_procesos(total: int, n_chunks: int = N_CHUNKS) -> int:
    """Mismo trabajo repartido en procesos: sí acelera (paralelismo real)."""
    chunks = partir_rango(total, n_chunks)
    with ProcessPoolExecutor(max_workers=n_chunks) as pool:
        return sum(pool.map(contar_primos, chunks))


# ---------------------------------------------------------------------------
# 6. Medición: timeit (micro-benchmarks) y cProfile (perfil detallado)
# ---------------------------------------------------------------------------


def medir_con_timeit(func, *args, repeticiones: int = 3, **kwargs) -> float:
    """
    timeit ejecuta la función varias veces y devuelve el mejor tiempo,
    minimizando ruido de scheduling del SO. Útil para comparar alternativas
    entre sí de forma justa.
    """
    timer = timeit.Timer(lambda: func(*args, **kwargs))
    tiempos = timer.repeat(repeat=repeticiones, number=1)
    return min(tiempos)


def perfilar_con_cprofile(func, *args, **kwargs):
    """
    cProfile da un desglose por función: cuántas veces se llamó, tiempo
    propio (tottime) y tiempo acumulado (cumtime). Sirve para encontrar
    *dónde* se va el tiempo dentro de una función, no solo cuánto tarda
    en total.
    """
    profiler = cProfile.Profile()
    profiler.enable()
    resultado = func(*args, **kwargs)
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(8)  # top 8 funciones por tiempo acumulado
    return resultado, stream.getvalue()


# ---------------------------------------------------------------------------
# 7. Correr todo y mostrar comparativa
# ---------------------------------------------------------------------------


def linea(titulo: str) -> None:
    print(f"\n{'=' * 70}\n{titulo}\n{'=' * 70}")


def demo_io_bound() -> None:
    linea(f"I/O-BOUND: {N_REQUESTS} requests, latencia simulada {LATENCY_S}s c/u")

    t_sync = medir_con_timeit(fetch_all_sync, URLS, repeticiones=1)
    print(
        f"[Síncrono]                 {t_sync:6.2f} s"
        f"  (teórico: {N_REQUESTS * LATENCY_S:.2f} s)"
    )

    t_threads = medir_con_timeit(fetch_all_threads, URLS, 10, repeticiones=1)
    print(
        f"[threading, 10 workers]    {t_threads:6.2f} s"
        f"  -> speedup x{t_sync / t_threads:.1f} vs síncrono"
    )

    t_async = medir_con_timeit(run_async_fetch, URLS, 10, repeticiones=1)
    print(
        f"[asyncio, semáforo(10)]    {t_async:6.2f} s"
        f"  -> speedup x{t_sync / t_async:.1f} vs síncrono"
    )

    # Con más concurrencia, asyncio suele escalar mejor que threads (menos
    # overhead por "worker" al no crear hilos de SO reales).
    t_async_40 = medir_con_timeit(run_async_fetch, URLS, 40, repeticiones=1)
    print(
        f"[asyncio, semáforo(40)]    {t_async_40:6.2f} s"
        f"  -> speedup x{t_sync / t_async_40:.1f} vs síncrono"
    )


def demo_cpu_bound() -> None:
    linea(f"CPU-BOUND: contar primos en [0, {NUMEROS_A_PROBAR}) — GIL en acción")

    t_seq = medir_con_timeit(contar_primos_secuencial, NUMEROS_A_PROBAR, repeticiones=1)
    print(f"[Secuencial]                  {t_seq:6.2f} s")

    t_threads = medir_con_timeit(
        contar_primos_threads, NUMEROS_A_PROBAR, N_CHUNKS, repeticiones=1
    )
    print(
        f"[threading, {N_CHUNKS} workers]      {t_threads:6.2f} s"
        f"  -> speedup x{t_seq / t_threads:.2f}  (GIL: casi nulo o negativo)"
    )

    t_procs = medir_con_timeit(
        contar_primos_procesos, NUMEROS_A_PROBAR, N_CHUNKS, repeticiones=1
    )
    print(
        f"[multiprocessing, {N_CHUNKS} workers]{t_procs:6.2f} s"
        f"  -> speedup x{t_seq / t_procs:.2f}  (paralelismo real)"
    )


def demo_cprofile() -> None:
    linea("cProfile sobre la versión síncrona (para ver dónde se va el tiempo)")
    _, reporte = perfilar_con_cprofile(fetch_all_sync, URLS)
    print(reporte)


def main() -> None:
    server = start_test_server()
    try:
        # calentar conexión TCP para no medir el primer "cold start"
        with httpx.Client() as c:
            c.get(URLS[0])

        demo_io_bound()
        demo_cpu_bound()
        demo_cprofile()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
