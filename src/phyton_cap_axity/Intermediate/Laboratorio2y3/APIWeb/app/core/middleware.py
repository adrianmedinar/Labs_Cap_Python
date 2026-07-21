"""
Middlewares custom.

process_time_middleware: agrega header X-Process-Time (útil para monitoreo).
Se registra con @app.middleware("http") en main.py.
"""

import time
from collections.abc import Callable

from fastapi import Request


async def add_process_time_header(request: Request, call_next: Callable):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-ms"] = f"{duration_ms:.2f}"
    return response
