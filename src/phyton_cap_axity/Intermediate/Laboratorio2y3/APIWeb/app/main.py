"""
Punto de entrada de la aplicación.

Ejecutar en desarrollo:
    uvicorn app.main:app --reload

Docs interactivas:
    /docs  (Swagger UI)
    /redoc (ReDoc)
"""

from contextlib import asynccontextmanager

from app.api.routers import auth, orders
from app.core.config import settings
from app.core.middleware import add_process_time_header
from app.db.session import Base, engine
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas al arrancar. En un proyecto real se usaría Alembic
    # para migraciones versionadas en vez de create_all.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=(
        "API de gestión de Órdenes con autenticación JWT. "
        "Incluye registro/login, CRUD protegido de órdenes y validación con Pydantic."
    ),
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Middleware custom ---
app.middleware("http")(add_process_time_header)


# --- Manejo uniforme de errores: respuesta JSON consistente en toda la API ---
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Error de validación", "errors": exc.errors()},
    )


# --- Routers ---
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(orders.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"], summary="Chequeo de salud del servicio")
async def health_check():
    return {"status": "ok"}
