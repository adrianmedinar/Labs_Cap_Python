# Orders API — FastAPI + JWT + SQLAlchemy Async

API REST de gestión de órdenes con autenticación JWT, validación con Pydantic,
CORS, middleware custom y tests de integración con base de datos temporal.

## Estructura del proyecto

```
app/
├── main.py                  # Ensamblado: app, CORS, middleware, exception handlers, routers
├── core/
│   ├── config.py             # Settings (env vars) con pydantic-settings
│   ├── security.py           # Hash de password + creación/validación de JWT
│   └── middleware.py         # Middleware custom (X-Process-Time header)
├── db/
│   └── session.py            # Engine async, Base declarativa, dependency get_db
├── models/                   # Modelos ORM (SQLAlchemy)
│   ├── user.py
│   └── order.py
├── schemas/                  # Schemas Pydantic (entrada/salida, validación, OpenAPI)
│   ├── user.py
│   ├── token.py
│   └── order.py
├── crud/                     # Acceso a datos, separado de la lógica HTTP
│   ├── user.py
│   └── order.py
└── api/
    ├── deps.py               # Dependencias compartidas: get_current_user (JWT guard)
    └── routers/
        ├── auth.py           # /auth/register, /auth/login
        └── orders.py         # CRUD de /orders (protegido)

tests/
├── conftest.py                # Fixtures: DB SQLite en memoria por test + cliente httpx
├── test_auth.py               # Tests de registro/login
└── test_orders.py             # Tests CRUD + aislamiento entre usuarios
```


```bash
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

##  Autenticación (JWT)

Flujo OAuth2 Password estándar, compatible con el botón "Authorize" de Swagger:

```bash
# 1. Registro
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"amedina@axity.net","password":"Clav3$egur@123"}'

# 2. Login (form-data, no JSON)
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=amedina@axity.net&password=Clav3$egur@123"

# 3. Usar el token
curl http://127.0.0.1:8000/api/v1/orders \
  -H "Authorization: Bearer <access_token>"

## Endpoints

| Método | Ruta                     | Auth | Descripción                    |
|--------|--------------------------|------|---------------------------------|
| POST   | `/api/v1/auth/register`  | No   | Crear usuario                   |
| POST   | `/api/v1/auth/login`     | No   | Login, devuelve JWT             |
| POST   | `/api/v1/orders`         | Sí   | Crear orden                     |
| GET    | `/api/v1/orders`         | Sí   | Listar mis órdenes (paginado)   |
| GET    | `/api/v1/orders/{id}`    | Sí   | Obtener una orden               |
| PATCH  | `/api/v1/orders/{id}`    | Sí   | Actualizar parcialmente         |
| DELETE | `/api/v1/orders/{id}`    | Sí   | Eliminar orden                  |
| GET    | `/health`                | No   | Health check                    |

## Validación (Pydantic)

- `quantity`: entero, `> 0`, `<= 10000`.
- `unit_price`: float, `> 0`.
- `item`: string no vacío tras `strip()`.
- `email`: validado con `EmailStr` (formato RFC).
- `password`: mínimo 8 caracteres en el registro.

Cualquier violación devuelve `422` con el detalle de qué campo falló

## Tests

```bash
pytest -v
```