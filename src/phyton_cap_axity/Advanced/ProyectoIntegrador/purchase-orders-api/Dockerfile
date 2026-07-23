# syntax=docker/dockerfile:1

# ==============================================================================
# Etapa 1: builder — instala dependencias en un entorno aislado
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Dependencias de sistema mínimas para compilar bcrypt/asyncpg si hiciera falta
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && \
    pip install --prefix=/install ".[dev]" && \
    pip install --prefix=/install "bcrypt>=4.0.1,<4.1.0" --force-reinstall

# ==============================================================================
# Etapa 2: runtime — imagen final, mínima, sin herramientas de build
# ==============================================================================
FROM python:3.12-slim AS runtime

# Usuario no-root por seguridad
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY pyproject.toml ./pyproject.toml

RUN chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "purchase_orders.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
