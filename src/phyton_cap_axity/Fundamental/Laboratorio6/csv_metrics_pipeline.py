#!/usr/bin/env python3
"""
csv_metrics_pipeline.py
------------------------
Pipeline que:
  1. Ingiere un archivo CSV (csv.DictReader).
  2. Calcula métricas por columna (numéricas y categóricas).
  3. Exporta el resultado a JSON de forma atómica.
  4. Registra todo con logging estructurado (consola + archivo JSON rotativo).
  5. Permite configuración opcional vía YAML.
  6. Ejecuta un comando de post-proceso opcional vía subprocess (ej. compresión).

Términos técnicos cubiertos:
  - pathlib y manejo seguro de archivos/rutas
  - csv / json / yaml: parseo y serialización
  - datetime y zonas horarias (zoneinfo)
  - logging y configuración (dictConfig)
  - subprocess y automatización

Uso:
    python csv_metrics_pipeline.py --input datos_csv.csv --output salida/metrics.json
    python csv_metrics_pipeline.py --input datos_csv.csv --config config.yaml --output salida/metrics.json
    python csv_metrics_pipeline.py --input datos_csv.csv --config config.yaml --log-level DEBUG
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import logging
import logging.config
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# --------------------------------------------------------------------------
# 1. LOGGING ESTRUCTURADO
# --------------------------------------------------------------------------


class JsonFormatter(logging.Formatter):
    """Formatea cada registro de log como una línea JSON (logging estructurado)."""

    def __init__(self, tz: ZoneInfo | timezone = timezone.utc) -> None:
        super().__init__()
        self.tz = tz

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=self.tz).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(log_level: str, log_dir: Path, tz: ZoneInfo) -> logging.Logger:
    """Configura logging con dictConfig: consola legible + archivo JSON rotativo."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "pipeline.log"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": lambda: JsonFormatter(tz=tz),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": log_level,
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "level": "DEBUG",
                "filename": str(log_file),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
        },
    }
    logging.config.dictConfig(config)
    return logging.getLogger("csv_metrics_pipeline")


# --------------------------------------------------------------------------
# 2. MANEJO SEGURO DE RUTAS (pathlib)
# --------------------------------------------------------------------------


def safe_resolve(path: Path, base_dir: Path, must_exist: bool = False) -> Path:
    """
    Resuelve una ruta garantizando que quede DENTRO de base_dir
    (protección contra path traversal, ej. '../../etc/passwd').
    """
    base_resolved = base_dir.resolve()
    candidate = path if path.is_absolute() else base_resolved / path
    resolved = candidate.resolve()

    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError(
            f"Ruta fuera del directorio permitido ({base_resolved}): {resolved}"
        )

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"No existe la ruta requerida: {resolved}")

    return resolved


# --------------------------------------------------------------------------
# 3. INGESTA CSV
# --------------------------------------------------------------------------


def read_csv_rows(csv_path: Path, logger: logging.Logger) -> list[dict]:
    """Lee un CSV con csv.DictReader manejando errores de parseo/codificación."""
    rows: list[dict] = []
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        logger.info(
            "CSV leído correctamente: %d filas desde '%s'", len(rows), csv_path.name
        )
    except csv.Error as e:
        logger.error("Error de parseo CSV en %s: %s", csv_path, e)
        raise
    except UnicodeDecodeError as e:
        logger.error("Error de codificación en %s: %s", csv_path, e)
        raise
    return rows


# --------------------------------------------------------------------------
# 4. CONFIGURACIÓN YAML (opcional)
# --------------------------------------------------------------------------


def load_config(config_path: Path | None, logger: logging.Logger) -> dict:
    """Carga configuración YAML opcional; si no hay archivo o PyYAML, usa defaults."""
    default_config = {
        "timezone": "America/Mexico_City",
        "json_indent": 2,
        "post_process_command": None,  # ej: ["gzip", "-f", "{output}"]
    }
    if config_path is None:
        logger.info("Sin config.yaml: usando configuración por defecto")
        return default_config

    try:
        import yaml  # PyYAML
    except ImportError:
        logger.warning(
            "PyYAML no está instalado; usando configuración por defecto. "
            "Instala con: pip install pyyaml"
        )
        return default_config

    try:
        with config_path.open("r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        default_config.update(user_config)
        logger.info("Configuración cargada desde '%s'", config_path.name)
    except yaml.YAMLError as e:
        logger.error("Error de parseo YAML en %s: %s", config_path, e)
        raise

    return default_config


def resolve_timezone(name: str, logger: logging.Logger) -> ZoneInfo:
    """
    Resuelve el nombre de zona horaria a un objeto ZoneInfo.
    En Windows, 'zoneinfo' no trae datos de zonas horarias del sistema operativo
    (a diferencia de Linux/Mac) y requiere el paquete 'tzdata' instalado
    (pip install tzdata). Si falta, se informa claramente y se usa UTC como
    respaldo para no detener el pipeline.
    """
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        logger.error(
            "No se encontró la zona horaria '%s'. "
            "En Windows esto normalmente se soluciona instalando el paquete "
            "'tzdata' con: pip install tzdata. Usando UTC como respaldo.",
            name,
        )
        return ZoneInfo("UTC")


# --------------------------------------------------------------------------
# 5. CÁLCULO DE MÉTRICAS (datetime + zoneinfo)
# --------------------------------------------------------------------------


def compute_metrics(rows: list[dict], tz: ZoneInfo, logger: logging.Logger) -> dict:
    """Calcula métricas numéricas y categóricas por columna."""
    start = datetime.now(tz)
    metrics: dict = {
        "generated_at": start.isoformat(),
        "timezone": str(tz),
        "total_rows": len(rows),
        "columns": {},
    }

    if not rows:
        logger.warning("El CSV no contiene filas; se exportarán métricas vacías")
        metrics["processing_seconds"] = 0.0
        return metrics

    columns = rows[0].keys()
    for col in columns:
        values = [r.get(col, "") for r in rows]
        numeric_values: list[float] = []
        for v in values:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                continue

        is_numeric = len(numeric_values) > 0 and len(numeric_values) >= 0.8 * len(
            values
        )

        if is_numeric:
            metrics["columns"][col] = {
                "tipo": "numeric",
                "total": len(numeric_values),
                "suma": round(sum(numeric_values), 4),
                "promedio": round(statistics.mean(numeric_values), 4),
                "min": min(numeric_values),
                "max": max(numeric_values),
                "desv.std": (
                    round(statistics.pstdev(numeric_values), 4)
                    if len(numeric_values) > 1
                    else 0.0
                ),
            }
        else:
            counter = collections.Counter(values)
            metrics["columns"][col] = {
                "type": "categorical",
                "unique_values": len(counter),
                "most_common": counter.most_common(3),
            }

    elapsed = (datetime.now(tz) - start).total_seconds()
    metrics["processing_seconds"] = round(elapsed, 6)
    logger.info("Métricas calculadas para %d columnas en %.4fs", len(columns), elapsed)
    return metrics


# --------------------------------------------------------------------------
# 6. EXPORTACIÓN JSON (escritura atómica y segura)
# --------------------------------------------------------------------------


def export_json(
    data: dict, output_path: Path, logger: logging.Logger, indent: int = 2
) -> None:
    """Escribe JSON de forma atómica: escribe a .tmp y luego reemplaza (evita archivos corruptos)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
        tmp_path.replace(output_path)  # operación atómica en la mayoría de sistemas
        logger.info("JSON exportado en: %s", output_path)
    except (OSError, TypeError) as e:
        logger.error("Error exportando JSON: %s", e)
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


# --------------------------------------------------------------------------
# 7. SUBPROCESS Y AUTOMATIZACIÓN
# --------------------------------------------------------------------------


def run_post_process(
    command_template: list[str], output_path: Path, logger: logging.Logger
) -> None:
    """
    Ejecuta un comando externo de post-proceso (ej. compresión, checksum).
    Usa lista de argumentos (NO shell=True) para evitar inyección de comandos.
    """
    command = [part.format(output=str(output_path)) for part in command_template]
    logger.info("Ejecutando post-proceso: %s", " ".join(command))

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.stdout.strip():
            logger.debug("stdout post-proceso: %s", result.stdout.strip())
        logger.info("Post-proceso completado correctamente")
    except FileNotFoundError:
        logger.error("Comando no encontrado: '%s'", command[0])
    except subprocess.CalledProcessError as e:
        logger.error(
            "Post-proceso falló (código %s): %s", e.returncode, e.stderr.strip()
        )
    except subprocess.TimeoutExpired:
        logger.error("Post-proceso excedió el tiempo límite de 30s")


# --------------------------------------------------------------------------
# Argumento script y flujo principal
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline CSV -> métricas -> JSON con logging estructurado"
    )
    parser.add_argument("--input", required=True, help="Ruta al CSV de entrada")
    parser.add_argument(
        "--output", default="output/metrics.json", help="Ruta al JSON de salida"
    )
    parser.add_argument("--config", default=None, help="Ruta a config YAML opcional")
    parser.add_argument(
        "--base-dir", default=".", help="Directorio base permitido (seguridad de rutas)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument("--log-dir", default="logs", help="Directorio para los logs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base_dir = Path(args.base_dir)

    # Config y timezone se necesitan antes de tener logger completo,
    # así que usamos un logger mínimo temporal para esta fase.
    bootstrap_logger = logging.getLogger("bootstrap")
    logging.basicConfig(level="INFO")

    try:
        config_path = (
            safe_resolve(Path(args.config), base_dir, must_exist=True)
            if args.config
            else None
        )
    except (ValueError, FileNotFoundError) as e:
        bootstrap_logger.error("Ruta de config inválida: %s", e)
        return 1

    config = load_config(config_path, bootstrap_logger)
    tz = resolve_timezone(
        config.get("timezone", "America/Mexico_City"), bootstrap_logger
    )

    logger = setup_logging(args.log_level, Path(args.log_dir), tz)
    logger.info("=== Iniciando pipeline CSV -> métricas -> JSON ===")

    try:
        input_path = safe_resolve(Path(args.input), base_dir, must_exist=True)
        output_path = safe_resolve(Path(args.output), base_dir, must_exist=False)
    except (ValueError, FileNotFoundError) as e:
        logger.error("Error de validación de rutas: %s", e)
        return 1

    try:
        rows = read_csv_rows(input_path, logger)
        metrics = compute_metrics(rows, tz, logger)
        export_json(metrics, output_path, logger, indent=config.get("json_indent", 2))

        post_cmd = config.get("post_process_command")
        if post_cmd:
            run_post_process(post_cmd, output_path, logger)

    except Exception:
        logger.exception("Fallo no controlado durante la ejecución del pipeline")
        return 1

    logger.info("=== Pipeline finalizado correctamente ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
