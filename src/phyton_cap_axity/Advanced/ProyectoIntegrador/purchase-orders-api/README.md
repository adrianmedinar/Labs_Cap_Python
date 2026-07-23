# Purchase Orders API

API REST para la gestión del ciclo de vida completo de **Órdenes de Compra**,
construida con **arquitectura hexagonal** (Ports & Adapters), autenticación
JWT, y una suite de pruebas en 4 capas (unitarias, integración, contrato, E2E).

```
DRAFT --submit--> PENDING_APPROVAL --approve--> APPROVED --send-to-supplier--> SENT_TO_SUPPLIER
                        |                            |                                |
                     reject                       cancel                     confirm-receipt
                        v                            v                                v
                    REJECTED                     CANCELLED                        RECEIVED
                                                                                        |
                                                                                      close
                                                                                        v
                                                                                     CLOSED
```

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Diagramas](#diagramas)
3. [Requisitos](#requisitos)
4. [Instalación](#instalación)
5. [Configuración (variables de entorno)](#configuración-variables-de-entorno)
6. [Migraciones de base de datos](#migraciones-de-base-de-datos)
7. [Ejecutar la API](#ejecutar-la-api)
8. [Uso rápido (curl)](#uso-rápido-curl)
9. [Ejecutar pruebas](#ejecutar-pruebas)
10. [Calidad de código (lint / tipado)](#calidad-de-código-lint--tipado)
11. [Auditoría de dependencias](#auditoría-de-dependencias)
12. [CI/CD](#cicd)
13. [Docker y Docker Compose](#docker-y-docker-compose)
14. [GitHub Codespaces](#github-codespaces)
15. [Estructura del proyecto](#estructura-del-proyecto)
16. [Reglas de negocio](#reglas-de-negocio)
17. [Solución de problemas](#solución-de-problemas)

---

## Arquitectura

El proyecto sigue **arquitectura hexagonal** (dominio → aplicación →
infraestructura/API), donde las dependencias siempre apuntan hacia adentro:

```
┌─────────────────────────────────────────────────────────────────┐
│  API (FastAPI)                                                  │
│  routers/ · schemas/ · dependencies.py · error_handlers.py       │
└───────────────────────────┬───────────────────────────────────--┘
                            │ usa
┌───────────────────────────▼───────────────────────────────────--┐
│  Aplicación (casos de uso)                                       │
│  use_cases/ · dtos/ · mappers.py                                  │
└───────────────────────────┬───────────────────────────────────--┘
                            │ depende de (interfaces)
┌───────────────────────────▼───────────────────────────────────--┐
│  Dominio (puro, sin frameworks)                                  │
│  entities/ · value_objects/ · services/ · ports/ · exceptions/    │
└───────────────────────────▲───────────────────────────────────--┘
                            │ implementa
┌───────────────────────────┴───────────────────────────────────--┐
│  Infraestructura (adaptadores concretos)                         │
│  db/ (SQLAlchemy + Alembic) · security/ (JWT, bcrypt) · container │
└─────────────────────────────────────────────────────────────────┘
```

- **Dominio**: entidades (`PurchaseOrder`, `Supplier`, `User`), value objects
  (`Money`, `LineItem`, `PurchaseOrderStatus`), servicio de dominio
  (`ApprovalPolicy`) y **puertos** (interfaces `ABC`) que definen los
  contratos que la infraestructura debe implementar. No importa nada de
  FastAPI, SQLAlchemy ni Pydantic.
- **Aplicación**: casos de uso (uno por operación de negocio), orquestando
  puertos del dominio mediante un patrón `UnitOfWork`. Usa DTOs propios
  (`dataclasses`), independientes de Pydantic.
- **Infraestructura**: implementaciones concretas de los puertos —
  repositorios SQLAlchemy async, `JwtTokenProvider` (PyJWT),
  `BcryptPasswordHasher` (passlib), y el `Container` (composition root).
- **API**: FastAPI expone los casos de uso vía HTTP, traduce DTOs ↔ schemas
  Pydantic, y traduce excepciones de negocio a códigos HTTP.

---

## Diagramas

Los diagramas completos (arquitectura, máquina de estados, secuencia de un
flujo de aprobación, modelo entidad-relación y pipeline de CI/CD) están en
**[`docs/diagrams/README.md`](docs/diagrams/README.md)**, escritos en
Mermaid y renderizados automáticamente al verlos en GitHub.

---

## Requisitos

| Herramienta | Versión mínima | Notas |
|---|---|---|
| Python | 3.12 | usa `sqlite+aiosqlite` por defecto para desarrollo local |
| pip | 23+ | para instalar en modo editable |
| PostgreSQL | 14+ | opcional en local |
| Git | cualquiera | |

No se requiere Docker para correr localmente (SQLite funciona out-of-the-box),
pero si vas a usar Postgres necesitas una instancia corriendo y accesible.

---

## Instalación

```bash
# 1. Clonar el repositorio y entrar a la carpeta
git clone <url-del-repo>
cd purchase-orders-api

# 2. Crear y activar un entorno virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Instalar el proyecto en modo editable + dependencias de desarrollo
pip install --upgrade pip
pip install -e ".[dev]"
```

> ⚠️ **Nota sobre `bcrypt`**: el proyecto fija `bcrypt>=4.0.1,<4.1.0` en
> `pyproject.toml` porque `passlib==1.7.4` (última versión publicada) es
> incompatible con `bcrypt>=4.1`. Si ves un error de `AttributeError:
> module 'bcrypt' has no attribute '__about__'` al hashear contraseñas,
> confirma que se instaló esa versión fijada:
> ```bash
> pip install "bcrypt>=4.0.1,<4.1.0" --force-reinstall
> ```

---

## Configuración (variables de entorno)

Copia el archivo de ejemplo y ajusta los valores:

```bash
cp .env.example .env
```

| Variable | Descripción | Default |
|---|---|---|
| `ENVIRONMENT` | `development` \| `staging` \| `production` | `development` |
| `DEBUG` | Habilita modo debug | `true` |
| `DATABASE_URL` | URL async de conexión. Postgres: `postgresql+asyncpg://user:pass@host:5432/db`. SQLite: `sqlite+aiosqlite:///./purchase_orders.db` | `sqlite+aiosqlite:///./purchase_orders.db` |
| `DATABASE_ECHO` | Loggea el SQL generado por SQLAlchemy | `false` |
| `JWT_SECRET_KEY` | Secreto para firmar JWT. **Genera uno fuerte**: `openssl rand -hex 32` | *(placeholder, cámbialo)* |
| `JWT_ALGORITHM` | Algoritmo de firma | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración del token | `30` |
| `API_TITLE` / `API_VERSION` | Metadata mostrada en `/docs` | — |
| `CORS_ALLOWED_ORIGINS` | Lista JSON de orígenes permitidos | `["http://localhost:3000"]` |

---

## Migraciones de base de datos

Las migraciones usan **Alembic** en modo async y toman la URL de conexión
directamente de `Settings` (variables de entorno), no de `alembic.ini`.

```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Generar una nueva migración a partir de cambios en los modelos ORM
# (src/purchase_orders/infrastructure/db/models.py)
alembic revision --autogenerate -m "descripción del cambio"

# Revertir la última migración
alembic downgrade -1

# Revertir todo (deja la BD vacía)
alembic downgrade base
```

> Con SQLite (`sqlite+aiosqlite:///./purchase_orders.db`), el archivo de
> base de datos se crea automáticamente en la raíz del proyecto al correr
> `alembic upgrade head`.

---

## Ejecutar la API

```bash
# Modo desarrollo (recarga automática)
uvicorn purchase_orders.api.main:app --reload --host 0.0.0.0 --port 8000

```

Una vez arriba:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **Health check**: http://localhost:8000/health

### Autenticación desde Swagger UI

1. Registra un usuario en `POST /api/v1/auth/register` (elige un `role`:
   `requester`, `approver_junior`, `approver_senior` o `admin`).
2. Haz clic en el botón **Authorize** (candado, arriba a la derecha) e
   ingresa el `username`/`password` — el login usa el flujo estándar
   OAuth2 Password, compatible directamente con ese botón.
3. Todos los endpoints protegidos ahora incluirán el header
   `Authorization: Bearer <token>` automáticamente.

---

## Uso rápido (curl)

```bash
BASE_URL="http://localhost:8000/api/v1"

# 1. Registrar un usuario aprobador
curl -X POST "$BASE_URL/auth/register" -H "Content-Type: application/json" -d '{
  "username": "jane", "email": "jane@corp.com", "password": "secret123", "role": "approver_senior"
}'

# 2. Login (form-urlencoded, NO json)
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -d "username=jane&password=secret123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Crear un proveedor
SUPPLIER_ID=$(curl -s -X POST "$BASE_URL/suppliers" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "tax_id": "RFC-123", "email": "ventas@acme.com"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 4. Crear una orden de compra
ORDER_ID=$(curl -s -X POST "$BASE_URL/purchase-orders" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"supplier_id\": \"$SUPPLIER_ID\", \"currency\": \"USD\", \"line_items\": [
        {\"sku\": \"SKU-1\", \"description\": \"Laptop\", \"quantity\": 2, \"unit_price\": \"1500.00\"}
      ]}" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 5. Enviar a aprobación y aprobar
curl -X POST "$BASE_URL/purchase-orders/$ORDER_ID/submit" -H "Authorization: Bearer $TOKEN"
curl -X POST "$BASE_URL/purchase-orders/$ORDER_ID/approve" -H "Authorization: Bearer $TOKEN"
```

---

## Ejecutar pruebas

```bash
# Suite completa (unitarias + integración + contrato + e2e), con cobertura
pytest

# Solo una categoría (marcadores definidos en pyproject.toml)
pytest -m unit
pytest -m integration
pytest -m contract
pytest -m e2e

# Un archivo o prueba específica
pytest tests/unit/domain/test_purchase_order.py -v
pytest tests/e2e/test_purchase_order_lifecycle.py::TestFlujoCompletoDeAprobacion -v

# Ver reporte de cobertura HTML
pytest --cov-report=html
open htmlcov/index.html   # macOS; en Linux: xdg-open htmlcov/index.html
```

La suite corre contra **SQLite en memoria** (fixtures en `tests/conftest.py`),
por lo que no necesitas Postgres para ejecutar las pruebas localmente ni en CI.

Umbral mínimo de cobertura configurado: **80%** (`pyproject.toml`, falla el
comando `pytest` si no se alcanza).

---

## Calidad de código (lint / tipado)

```bash
# Lint (estilo, imports, buenas prácticas)
ruff check src tests

# Autofix de lo que sea corregible automáticamente
ruff check src tests --fix

# Formateo
ruff format src tests

# Tipado estático
mypy src
```

---

## Auditoría de dependencias

```bash
pip-audit
```

Revisa vulnerabilidades conocidas (bases de datos OSV / PyPA Advisory) en
todas las dependencias instaladas. Ver **[`docs/audit/README.md`](docs/audit/README.md)**
para la evidencia completa de la última auditoría realizada (incluye
vulnerabilidades reales encontradas y su remediación) y los artefactos:
[`pip-audit-report.json`](docs/audit/pip-audit-report.json),
[`pip-audit-report.txt`](docs/audit/pip-audit-report.txt) y
[`requirements-freeze-audited.txt`](docs/audit/requirements-freeze-audited.txt).

Este comando también corre automáticamente:
- En **cada push/PR** (job `dependency-audit` en CI) — **falla el build**
  si aparece una vulnerabilidad conocida.
- **Semanalmente** (cron), para detectar CVEs publicados después del
  último cambio de código.
- **Dependabot** (`.github/dependabot.yml`) abre PRs semanales de
  actualización de dependencias de Python, GitHub Actions y la imagen
  Docker base.

---

## CI/CD

El pipeline (`.github/workflows/ci.yml`) corre en cada push/PR a `main` y
`develop`, y semanalmente por cron. Jobs:

| Job | Qué hace | Bloquea el build si falla |
|---|---|---|
| `lint` | `ruff check` + `ruff format --check` | Sí |
| `typecheck` | `mypy src` | Sí |
| `test` | Suite completa (115 pruebas) + cobertura (umbral 80%), publica `coverage.xml` como artefacto | Sí |
| `dependency-audit` | `pip-audit`, publica el reporte JSON como artefacto (retención 90 días) | Sí |
| `migration-check` | `alembic upgrade head` → `downgrade base` → `upgrade head`, verifica reversibilidad | Sí |
| `build` | Construye paquete Python (`sdist`+`wheel`) y la imagen Docker (sin publicar); depende de todos los anteriores | Sí |
| `publish-image` | Publica la imagen en GHCR (`ghcr.io/<owner>/<repo>`), solo en push a `main` | — |

```bash
# Reproducir localmente lo que hace el job `test` de CI
pytest --cov-report=xml --cov-report=term-missing

# Reproducir el job `migration-check`
DATABASE_URL="sqlite+aiosqlite:///./ci_check.db" JWT_SECRET_KEY="local-test-secret-32-characters-ok" alembic upgrade head
DATABASE_URL="sqlite+aiosqlite:///./ci_check.db" JWT_SECRET_KEY="local-test-secret-32-characters-ok" alembic downgrade base
```

---

## Docker y Docker Compose

```bash
# Levantar API + PostgreSQL (con migración automática al iniciar)
docker compose up --build

# La API queda disponible en http://localhost:8000/docs

# Detener y limpiar
docker compose down          # conserva el volumen de datos de Postgres
docker compose down -v       # también elimina el volumen (borra los datos)
```

El `Dockerfile` es multi-stage: una etapa `builder` instala las
dependencias en un prefix aislado, y la etapa `runtime` final es una
imagen mínima (`python:3.12-slim`) que corre como usuario no-root y
expone un `HEALTHCHECK` sobre `/health`.

Para construir y correr solo la imagen (usando SQLite, sin Postgres):

```bash
docker build -t purchase-orders-api .
docker run -p 8000:8000 \
  -e DATABASE_URL="sqlite+aiosqlite:////app/purchase_orders.db" \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  purchase-orders-api
```

---

## GitHub Codespaces

El proyecto incluye `.devcontainer/devcontainer.json`, por lo que puedes
abrirlo directamente en un Codespace (botón **Code → Codespaces → Create
codespace** en GitHub) sin configuración manual:

1. El `postCreateCommand` (`.devcontainer/post-create.sh`) automáticamente:
   - crea el entorno virtual e instala todas las dependencias,
   - genera un `.env` con SQLite + un `JWT_SECRET_KEY` aleatorio,
   - aplica las migraciones (`alembic upgrade head`).
2. Al terminar, solo falta:
   ```bash
   source .venv/bin/activate
   uvicorn purchase_orders.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. El puerto `8000` se reenvía automáticamente (verás una notificación de
   VS Code); ábrelo para llegar a `/docs`.

El devcontainer viene preconfigurado con extensiones de VS Code para
Python, Ruff (lint + formato al guardar) y mypy.

---

## Estructura del proyecto

```
purchase-orders-api/
├── src/purchase_orders/
│   ├── domain/                    # Lógica de negocio pura (sin frameworks)
│   │   ├── entities/               # PurchaseOrder (agregado raíz), Supplier, User
│   │   ├── value_objects/          # Money, LineItem, PurchaseOrderStatus
│   │   ├── services/               # ApprovalPolicy
│   │   ├── ports/                  # Interfaces (repos, hasher, JWT, UoW)
│   │   └── exceptions/             # Excepciones de negocio
│   ├── application/                # Casos de uso + DTOs
│   │   ├── use_cases/
│   │   ├── dtos/
│   │   ├── mappers.py
│   │   └── exceptions.py
│   ├── infrastructure/             # Adaptadores concretos
│   │   ├── db/                     # SQLAlchemy: modelos, repos, UoW
│   │   ├── security/                # JWT (PyJWT), hashing (passlib/bcrypt)
│   │   ├── config.py                 # Settings (pydantic-settings)
│   │   └── container.py              # Composition root (DI)
│   └── api/                        # FastAPI
│       ├── routers/                  # auth, suppliers, purchase-orders
│       ├── schemas/                  # Contratos Pydantic request/response
│       ├── dependencies.py           # DI de FastAPI + JWT (OAuth2PasswordBearer)
│       ├── error_handlers.py         # Traducción excepciones → HTTP
│       └── main.py                   # create_app() factory
├── tests/
│   ├── unit/                       # Dominio puro + casos de uso con fakes
│   ├── integration/                # Repositorios SQLAlchemy contra SQLite real
│   ├── contract/                   # Esquema OpenAPI, forma de respuestas
│   ├── e2e/                        # Ciclo de vida completo vía HTTP
│   ├── support/fakes.py            # Adaptadores fake en memoria
│   └── conftest.py                 # Fixtures compartidos
├── migrations/                     # Alembic (async)
├── docs/
│   ├── audit/                       # Evidencia de auditoría de dependencias
│   └── diagrams/                    # Diagramas Mermaid (arquitectura, estados, secuencia, ER, CI/CD)
├── .github/
│   ├── workflows/ci.yml            # Pipeline de CI/CD (lint/tipado/tests/audit/build)
│   └── dependabot.yml               # Actualizaciones automáticas de dependencias
├── .devcontainer/                  # GitHub Codespaces
│   ├── devcontainer.json
│   └── post-create.sh
├── Dockerfile                      # Imagen multi-stage
├── docker-compose.yml              # API + PostgreSQL local
├── pyproject.toml                  # Dependencias + config de ruff/mypy/pytest
├── alembic.ini
└── .env.example
```

---

## Reglas de negocio

- **Máquina de estados** de la orden (ver diagrama al inicio): las
  transiciones inválidas lanzan `InvalidPurchaseOrderStateError` → HTTP 409.
- Una orden **no puede existir sin ítems**; solo es editable en estado
  `DRAFT`.
- **Aprobación por rol** (`ApprovalPolicy`): cada rol tiene un monto máximo
  autorizable (`approver_junior` < `approver_senior` < `admin`). Si el total
  de la orden excede el límite del rol → HTTP 403
  (`ApprovalThresholdExceededError`).
- **Control de concurrencia optimista**: cada orden tiene un campo
  `version`; si dos procesos intentan modificar la misma orden a partir de
  la misma versión leída, el segundo en escribir recibe HTTP 409
  (`ConcurrentModificationError`).
- `Money` es inmutable, siempre normalizado a 2 decimales, y nunca permite
  operaciones entre monedas distintas (`CurrencyMismatchError`).

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `alembic revision --autogenerate` no detecta cambios en modelos | Falta importar el módulo de modelos antes de generar metadata | Verifica que `migrations/env.py` importe `purchase_orders.infrastructure.db.models` |
| `401 Unauthorized` en cualquier endpoint | Token vencido o `JWT_SECRET_KEY` distinto al usado para firmarlo | Vuelve a hacer login; confirma que `.env` no cambió entre el login y la request |

---