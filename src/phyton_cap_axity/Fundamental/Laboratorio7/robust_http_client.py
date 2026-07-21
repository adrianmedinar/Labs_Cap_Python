"""
robust_http_client.py
======================
Cliente HTTP robusto basado en httpx, con:

  1. Timeouts granulares (connect/read/write/pool) + reintentos
  2. Taxonomía de errores clara (transitorios vs. permanentes).
  3. Streaming de respuestas (descarga a disco sin cargar todo en RAM),
     con verificación de tamaño y reanudación opcional.

versión síncrona (RobustClient) y asíncrona (AsyncRobustClient).
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import httpx

logger = logging.getLogger("robust_http_client")


# ---------------------------------------------------------------------------
# 0. Logging estructurado (JSON)
# ---------------------------------------------------------------------------

# Atributos "de fábrica" de un LogRecord — todo lo que no esté aquí se asume
# que viene de `extra={...}` y se vuelca tal cual al JSON de salida.
_RESERVED_LOG_ATTRS = set(
    vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys()
) | {
    "message",
    "asctime",
}


class JSONFormatter(logging.Formatter):
    """Formatea cada LogRecord como una línea JSON (ideal para ELK/Datadog/CloudWatch)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Campos estructurados pasados vía extra={...}
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(
    level: int = logging.INFO, json_output: bool = True
) -> logging.Logger:
    """Configura el logger 'robust_http_client'. Llamar una vez al iniciar la app."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        JSONFormatter()
        if json_output
        else logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    lg = logging.getLogger("robust_http_client")
    lg.handlers.clear()
    lg.addHandler(handler)
    lg.setLevel(level)
    lg.propagate = False
    return lg


def _log(level: int, event: str, **fields) -> None:
    """Emite un log estructurado: event + campos arbitrarios (method, url, attempt, etc.)."""
    logger.log(level, event, extra={"event": event, **fields})


# ---------------------------------------------------------------------------
# 1. Configuración y taxonomía de errores
# ---------------------------------------------------------------------------


@dataclass
class RetryConfig:
    max_attempts: int = 4
    backoff_base: float = 0.5  # segundos, para el intento 1
    backoff_max: float = 20.0  # techo del backoff
    jitter: float = 0.25  # +/- fracción aleatoria sobre el backoff
    # Códigos de estado considerados transitorios (se reintentan)
    retry_statuses: frozenset[int] = field(
        default_factory=lambda: frozenset({408, 429, 500, 502, 503, 504})
    )
    # Métodos considerados "seguros" para reintentar automáticamente.
    idempotent_methods: frozenset[str] = field(
        default_factory=lambda: frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
    )


@dataclass
class TimeoutConfig:
    connect: float = 5.0
    read: float = 30.0
    write: float = 10.0
    pool: float = 5.0

    def to_httpx(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect, read=self.read, write=self.write, pool=self.pool
        )


class HttpClientError(Exception):
    """Error base — no se pudo completar la petición tras agotar reintentos."""


class TransientError(HttpClientError):
    """Error de red o 5xx/429 — reintentable, pero se agotaron los intentos."""


class PermanentError(HttpClientError):
    """Error 4xx (excepto 408/429) — no tiene sentido reintentar."""

    def __init__(self, response: httpx.Response):
        self.response = response
        super().__init__(
            f"{response.status_code} {response.reason_phrase}: {response.url}"
        )


class DownloadIntegrityError(HttpClientError):
    """El tamaño descargado no coincide con Content-Length."""


# ---------------------------------------------------------------------------
# 2. Lógica de backoff compartida
# ---------------------------------------------------------------------------


def _compute_backoff(
    attempt: int, cfg: RetryConfig, retry_after: Optional[float]
) -> float:
    """Calcula cuánto esperar antes del siguiente intento (attempt empieza en 1)."""
    if retry_after is not None:
        return min(retry_after, cfg.backoff_max)
    raw = min(cfg.backoff_base * (2 ** (attempt - 1)), cfg.backoff_max)
    jitter = raw * cfg.jitter
    return max(0.0, raw + random.uniform(-jitter, jitter))


def _parse_retry_after(response: httpx.Response) -> Optional[float]:
    val = response.headers.get("Retry-After")
    if not val:
        return None
    try:
        return float(val)  # formato en segundos
    except ValueError:
        return None  # (formato HTTP-date no soportado aquí; se ignora)


def _should_retry(
    method: str, cfg: RetryConfig, *, status: Optional[int], exc: Optional[Exception]
) -> bool:
    if method.upper() not in cfg.idempotent_methods:
        return False
    if exc is not None:
        # Errores de red/timeout: siempre transitorios
        return isinstance(
            exc,
            (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
                httpx.RemoteProtocolError,
            ),
        )
    if status is not None:
        return status in cfg.retry_statuses
    return False


# ---------------------------------------------------------------------------
# 3. Cliente SÍNCRONO
# ---------------------------------------------------------------------------


class RobustClient:
    def __init__(
        self,
        base_url: str = "",
        timeout: TimeoutConfig = TimeoutConfig(),
        retry: RetryConfig = RetryConfig(),
        http2: bool = True,
        max_connections: int = 100,
        max_keepalive: int = 20,
        headers: Optional[dict] = None,
    ):
        self.retry = retry
        limits = httpx.Limits(
            max_connections=max_connections, max_keepalive_connections=max_keepalive
        )
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout.to_httpx(),
            limits=limits,
            http2=http2,
            headers=headers,
            transport=httpx.HTTPTransport(
                retries=0
            ),  # los reintentos los hacemos nosotros
        )

    def __enter__(self) -> "RobustClient":
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._client.close()

    # -- petición con reintentos ------------------------------------------
    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        request_id = uuid.uuid4().hex[:12]
        t0 = time.monotonic()
        last_exc: Optional[Exception] = None
        _log(
            logging.INFO, "request_start", request_id=request_id, method=method, url=url
        )

        for attempt in range(1, self.retry.max_attempts + 1):
            try:
                resp = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self.retry.max_attempts and _should_retry(
                    method, self.retry, status=None, exc=exc
                ):
                    wait = _compute_backoff(attempt, self.retry, None)
                    _log(
                        logging.WARNING,
                        "request_retry",
                        request_id=request_id,
                        method=method,
                        url=url,
                        attempt=attempt,
                        max_attempts=self.retry.max_attempts,
                        error_type=type(exc).__name__,
                        error=str(exc),
                        wait_seconds=round(wait, 3),
                    )
                    time.sleep(wait)
                    continue
                _log(
                    logging.ERROR,
                    "request_failed_network",
                    request_id=request_id,
                    method=method,
                    url=url,
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    duration_ms=round((time.monotonic() - t0) * 1000, 1),
                )
                raise TransientError(
                    f"Fallo de red tras {attempt} intentos: {exc}"
                ) from exc

            if resp.status_code < 400:
                _log(
                    logging.INFO,
                    "request_success",
                    request_id=request_id,
                    method=method,
                    url=url,
                    status_code=resp.status_code,
                    attempt=attempt,
                    duration_ms=round((time.monotonic() - t0) * 1000, 1),
                )
                return resp

            if (
                resp.status_code in self.retry.retry_statuses
                and attempt < self.retry.max_attempts
            ):
                retry_after = _parse_retry_after(resp)
                wait = _compute_backoff(attempt, self.retry, retry_after)
                _log(
                    logging.WARNING,
                    "request_retry",
                    request_id=request_id,
                    method=method,
                    url=url,
                    attempt=attempt,
                    max_attempts=self.retry.max_attempts,
                    status_code=resp.status_code,
                    wait_seconds=round(wait, 3),
                    retry_after_header=retry_after,
                )
                resp.close()
                time.sleep(wait)
                continue

            duration_ms = round((time.monotonic() - t0) * 1000, 1)
            if resp.status_code in self.retry.retry_statuses:
                _log(
                    logging.ERROR,
                    "request_failed_transient",
                    request_id=request_id,
                    method=method,
                    url=url,
                    status_code=resp.status_code,
                    attempt=attempt,
                    duration_ms=duration_ms,
                )
                raise TransientError(
                    f"Status {resp.status_code} persistente tras {attempt} intentos"
                )
            _log(
                logging.ERROR,
                "request_failed_permanent",
                request_id=request_id,
                method=method,
                url=url,
                status_code=resp.status_code,
                attempt=attempt,
                duration_ms=duration_ms,
            )
            raise PermanentError(resp)

        raise TransientError(f"Reintentos agotados: {last_exc}")

    def get(self, url: str, **kw) -> httpx.Response:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw) -> httpx.Response:
        return self.request("POST", url, **kw)

    # -- descarga por streaming --------------------------------------------
    def download_to_file(
        self,
        url: str,
        dest: str | Path,
        *,
        chunk_size: int = 1024 * 64,
        resume: bool = False,
        progress_cb: Optional[Callable[[int, Optional[int]], None]] = None,
    ) -> Path:
        """
        Descarga `url` a `dest` sin cargar el archivo completo en memoria.
        - resume=True: si dest ya existe parcialmente, intenta reanudar con Range.
        - progress_cb(bytes_descargados, total_o_None): callback opcional de progreso.
        """
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        mode = "wb"
        headers = {}
        initial = 0
        request_id = uuid.uuid4().hex[:12]
        t0 = time.monotonic()

        if resume and dest.exists():
            initial = dest.stat().st_size
            headers["Range"] = f"bytes={initial}-"
            mode = "ab"

        _log(
            logging.INFO,
            "download_start",
            request_id=request_id,
            url=url,
            dest=str(dest),
            resume=resume,
            initial_bytes=initial,
        )

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retry.max_attempts + 1):
            try:
                with self._client.stream("GET", url, headers=headers) as resp:
                    if resp.status_code == 416:
                        # el archivo ya estaba completo
                        _log(
                            logging.INFO,
                            "download_already_complete",
                            request_id=request_id,
                            url=url,
                            dest=str(dest),
                        )
                        return dest
                    if (
                        resp.status_code >= 400
                        and resp.status_code not in self.retry.retry_statuses
                    ):
                        raise PermanentError(resp)
                    if resp.status_code in self.retry.retry_statuses:
                        raise TransientError(
                            f"Status {resp.status_code} al iniciar descarga"
                        )

                    total = resp.headers.get("Content-Length")
                    total_size = int(total) + initial if total else None
                    downloaded = initial

                    with open(dest, mode) as f:
                        for chunk in resp.iter_bytes(chunk_size=chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_cb:
                                progress_cb(downloaded, total_size)

                    if total_size is not None and downloaded != total_size:
                        raise DownloadIntegrityError(
                            f"Esperado {total_size} bytes, descargado {downloaded}"
                        )
                    _log(
                        logging.INFO,
                        "download_success",
                        request_id=request_id,
                        url=url,
                        dest=str(dest),
                        bytes_downloaded=downloaded,
                        attempt=attempt,
                        duration_ms=round((time.monotonic() - t0) * 1000, 1),
                    )
                    return dest

            except (httpx.HTTPError, TransientError) as exc:
                last_exc = exc
                if attempt < self.retry.max_attempts:
                    wait = _compute_backoff(attempt, self.retry, None)
                    _log(
                        logging.WARNING,
                        "download_retry",
                        request_id=request_id,
                        url=url,
                        dest=str(dest),
                        attempt=attempt,
                        max_attempts=self.retry.max_attempts,
                        error_type=type(exc).__name__,
                        error=str(exc),
                        wait_seconds=round(wait, 3),
                        resume=resume,
                    )
                    time.sleep(wait)
                    # si soportamos resume, actualizamos el offset para el próximo intento
                    if resume and dest.exists():
                        initial = dest.stat().st_size
                        headers["Range"] = f"bytes={initial}-"
                        mode = "ab"
                    continue
                _log(
                    logging.ERROR,
                    "download_failed",
                    request_id=request_id,
                    url=url,
                    dest=str(dest),
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    duration_ms=round((time.monotonic() - t0) * 1000, 1),
                )
                raise TransientError(
                    f"Descarga falló tras {attempt} intentos: {exc}"
                ) from exc

        raise TransientError(f"Reintentos agotados: {last_exc}")


# ---------------------------------------------------------------------------
# 4. Cliente ASÍNCRONO (misma lógica, con asyncio)
# ---------------------------------------------------------------------------


class AsyncRobustClient:
    def __init__(
        self,
        base_url: str = "",
        timeout: TimeoutConfig = TimeoutConfig(),
        retry: RetryConfig = RetryConfig(),
        http2: bool = True,
        max_connections: int = 100,
        max_keepalive: int = 20,
        headers: Optional[dict] = None,
    ):
        self.retry = retry
        limits = httpx.Limits(
            max_connections=max_connections, max_keepalive_connections=max_keepalive
        )
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout.to_httpx(),
            limits=limits,
            http2=http2,
            headers=headers,
            transport=httpx.AsyncHTTPTransport(retries=0),
        )

    async def __aenter__(self) -> "AsyncRobustClient":
        return self

    async def __aexit__(self, *exc):
        await self.aclose()

    async def aclose(self):
        await self._client.aclose()

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        request_id = uuid.uuid4().hex[:12]
        t0 = time.monotonic()
        last_exc: Optional[Exception] = None
        _log(
            logging.INFO, "request_start", request_id=request_id, method=method, url=url
        )

        for attempt in range(1, self.retry.max_attempts + 1):
            try:
                resp = await self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self.retry.max_attempts and _should_retry(
                    method, self.retry, status=None, exc=exc
                ):
                    wait = _compute_backoff(attempt, self.retry, None)
                    _log(
                        logging.WARNING,
                        "request_retry",
                        request_id=request_id,
                        method=method,
                        url=url,
                        attempt=attempt,
                        max_attempts=self.retry.max_attempts,
                        error_type=type(exc).__name__,
                        error=str(exc),
                        wait_seconds=round(wait, 3),
                    )
                    await asyncio.sleep(wait)
                    continue
                _log(
                    logging.ERROR,
                    "request_failed_network",
                    request_id=request_id,
                    method=method,
                    url=url,
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    duration_ms=round((time.monotonic() - t0) * 1000, 1),
                )
                raise TransientError(
                    f"Fallo de red tras {attempt} intentos: {exc}"
                ) from exc

            if resp.status_code < 400:
                _log(
                    logging.INFO,
                    "request_success",
                    request_id=request_id,
                    method=method,
                    url=url,
                    status_code=resp.status_code,
                    attempt=attempt,
                    duration_ms=round((time.monotonic() - t0) * 1000, 1),
                )
                return resp

            if (
                resp.status_code in self.retry.retry_statuses
                and attempt < self.retry.max_attempts
            ):
                retry_after = _parse_retry_after(resp)
                wait = _compute_backoff(attempt, self.retry, retry_after)
                _log(
                    logging.WARNING,
                    "request_retry",
                    request_id=request_id,
                    method=method,
                    url=url,
                    attempt=attempt,
                    max_attempts=self.retry.max_attempts,
                    status_code=resp.status_code,
                    wait_seconds=round(wait, 3),
                    retry_after_header=retry_after,
                )
                await resp.aclose()
                await asyncio.sleep(wait)
                continue

            duration_ms = round((time.monotonic() - t0) * 1000, 1)
            if resp.status_code in self.retry.retry_statuses:
                _log(
                    logging.ERROR,
                    "request_failed_transient",
                    request_id=request_id,
                    method=method,
                    url=url,
                    status_code=resp.status_code,
                    attempt=attempt,
                    duration_ms=duration_ms,
                )
                raise TransientError(
                    f"Status {resp.status_code} persistente tras {attempt} intentos"
                )
            _log(
                logging.ERROR,
                "request_failed_permanent",
                request_id=request_id,
                method=method,
                url=url,
                status_code=resp.status_code,
                attempt=attempt,
                duration_ms=duration_ms,
            )
            raise PermanentError(resp)

        raise TransientError(f"Reintentos agotados: {last_exc}")

    async def get(self, url: str, **kw) -> httpx.Response:
        return await self.request("GET", url, **kw)

    async def post(self, url: str, **kw) -> httpx.Response:
        return await self.request("POST", url, **kw)

    async def download_to_file(
        self,
        url: str,
        dest: str | Path,
        *,
        chunk_size: int = 1024 * 64,
        resume: bool = False,
        progress_cb: Optional[Callable[[int, Optional[int]], None]] = None,
    ) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        mode = "wb"
        headers = {}
        initial = 0
        request_id = uuid.uuid4().hex[:12]
        t0 = time.monotonic()

        if resume and dest.exists():
            initial = dest.stat().st_size
            headers["Range"] = f"bytes={initial}-"
            mode = "ab"

        _log(
            logging.INFO,
            "download_start",
            request_id=request_id,
            url=url,
            dest=str(dest),
            resume=resume,
            initial_bytes=initial,
        )

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retry.max_attempts + 1):
            try:
                async with self._client.stream("GET", url, headers=headers) as resp:
                    if resp.status_code == 416:
                        _log(
                            logging.INFO,
                            "download_already_complete",
                            request_id=request_id,
                            url=url,
                            dest=str(dest),
                        )
                        return dest
                    if (
                        resp.status_code >= 400
                        and resp.status_code not in self.retry.retry_statuses
                    ):
                        raise PermanentError(resp)
                    if resp.status_code in self.retry.retry_statuses:
                        raise TransientError(
                            f"Status {resp.status_code} al iniciar descarga"
                        )

                    total = resp.headers.get("Content-Length")
                    total_size = int(total) + initial if total else None
                    downloaded = initial

                    with open(dest, mode) as f:
                        async for chunk in resp.aiter_bytes(chunk_size=chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_cb:
                                progress_cb(downloaded, total_size)

                    if total_size is not None and downloaded != total_size:
                        raise DownloadIntegrityError(
                            f"Esperado {total_size} bytes, descargado {downloaded}"
                        )
                    _log(
                        logging.INFO,
                        "download_success",
                        request_id=request_id,
                        url=url,
                        dest=str(dest),
                        bytes_downloaded=downloaded,
                        attempt=attempt,
                        duration_ms=round((time.monotonic() - t0) * 1000, 1),
                    )
                    return dest

            except (httpx.HTTPError, TransientError) as exc:
                last_exc = exc
                if attempt < self.retry.max_attempts:
                    wait = _compute_backoff(attempt, self.retry, None)
                    _log(
                        logging.WARNING,
                        "download_retry",
                        request_id=request_id,
                        url=url,
                        dest=str(dest),
                        attempt=attempt,
                        max_attempts=self.retry.max_attempts,
                        error_type=type(exc).__name__,
                        error=str(exc),
                        wait_seconds=round(wait, 3),
                        resume=resume,
                    )
                    await asyncio.sleep(wait)
                    if resume and dest.exists():
                        initial = dest.stat().st_size
                        headers["Range"] = f"bytes={initial}-"
                        mode = "ab"
                    continue
                _log(
                    logging.ERROR,
                    "download_failed",
                    request_id=request_id,
                    url=url,
                    dest=str(dest),
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    duration_ms=round((time.monotonic() - t0) * 1000, 1),
                )
                raise TransientError(
                    f"Descarga falló tras {attempt} intentos: {exc}"
                ) from exc

        raise TransientError(f"Reintentos agotados: {last_exc}")


# ---------------------------------------------------------------------------
# 5. Ejemplo de uso
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    configure_logging(level=logging.INFO, json_output=True)

    # --- Uso síncrono ---
    with RobustClient(timeout=TimeoutConfig(connect=3, read=15)) as client:
        try:
            r = client.get("https://httpbin.org/get")
            print("GET status:", r.status_code)
        except PermanentError as e:
            print("Error permanente:", e)
        except TransientError as e:
            print("Error transitorio tras reintentos:", e)

        def progreso(descargado, total):
            if total:
                pct = descargado / total * 100
                print(f"\rDescargando... {pct:5.1f}%", end="")
            else:
                print(f"\rDescargando... {descargado} bytes", end="")

        try:
            path = client.download_to_file(
                "https://httpbin.org/bytes/1048576",
                "/tmp/ejemplo_descarga.bin",
                progress_cb=progreso,
            )
            print(f"\nArchivo guardado en: {path}")
        except HttpClientError as e:
            print("\nFalló la descarga:", e)

    # --- Uso asíncrono ---
    async def demo_async():
        async with AsyncRobustClient() as client:
            r = await client.get("https://httpbin.org/get")
            print("GET async status:", r.status_code)

    asyncio.run(demo_async())
