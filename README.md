
🟢 Fundamental Level
Entorno y Herramientas: Proyecto con Poetry, entornos virtuales, black, isort, ruff y pre-commit.

Fundamentos del Lenguaje: Script de procesamiento de JSON con filtrado, agregaciones y manejo de excepciones.

Funciones y Programación "Pythonic": Decorador de reintentos con backoff, generador por lotes y context manager para temporización.

Objetos y Modelos de Datos: dataclass Order con métodos derivados y validación/serialización con modelos de Pydantic.

Tipado Estático Opcional y Calidad: Type hints, comprobaciones con mypy y ruff, integración en pre-commit.

Librería Estándar y E/S: Ingesta de CSV, exportación JSON y logging estructurado.

HTTP y Consumo de APIs: Cliente con httpx que incluye reintentos, timeouts y streaming de descargas.

🟡 Intermediate Level
Acceso a Datos y ORM: Modelado de datos con SQLAlchemy, migraciones con Alembic y pruebas con SQLite en memoria.

APIs Web con FastAPI: CRUD de órdenes, autenticación JWT y tests de integración con pytest.

Pruebas y TDD: Desarrollo guiado por pruebas (TDD), property-based testing con Hypothesis y reporte de cobertura.

Concurrencia y Rendimiento: Cliente asíncrono concurrente con httpx.AsyncClient y Semaphore, y tareas CPU-bound con ProcessPoolExecutor.

Principios SOLID: Refactorización orientada a puertos (Protocol) e implementación de adaptadores cumpliendo LSP.

Patrones de Diseño: Implementación de patrones Strategy, Decorator y Adapter probados mediante pytest.

Ciencia de Datos: Procesamiento de datos en Pandas, entrenamiento/serialización de un modelo clasificador con scikit-learn y joblib.

Arquitectura Hexagonal: Implementación de casos de uso con adaptadores en memoria/SQL, notificaciones mockeadas y pruebas de contrato.

🔴 Advanced Level
Arquitectura Limpia: Reestructuración en capas independientes, Unit of Work, Presenter y eventos de dominio (OrderCreated).

Empaquetado, Distribución y CI/CD: Creación de ruedas (wheels), Dockerfile multistage y pipeline de CI/CD.

CLI y Automatización: Desarrollo de una CLI con Typer conectada a la API REST.

Seguridad y Mantenimiento: Uso de pydantic-settings, auditoría de vulnerabilidades con pip-audit/safety y hardening de contenedores Docker (usuario non-root).

Interoperabilidad y Ecosistema Mixto (Opcional): Servicios gRPC con Protobuf y mensajería orientada a eventos con RabbitMQ/Redis.

Proyecto Final Integrador: Aplicación completa con Arquitectura Hexagonal/Limpia, API con FastAPI, persistencia, pruebas E2E/contrato, contenerización y pipelines automáticos.




Gemini es una IA y puede cometer errores.

# Resumen de Laboratorios por Módulo

Este documento contiene una compilación y resumen estructurado de todos los laboratorios prácticos descritos en el plan de formación, organizados por nivel y módulo.

---

## 🟢 Fundamental Level

### 1. Entorno y Herramientas
* **Laboratorio:** 
  * Crear un proyecto con **Poetry** y activar el entorno virtual (`venv`).
  * Instalar herramientas de calidad y formato: `black`, `isort` y `ruff`.
  * Configurar `pre-commit` hooks y corregir infracciones iniciales a las reglas de estilo **PEP 8**.

### 2. Fundamentos del Lenguaje
* **Laboratorio:** 
  * Desarrollar un script en Python que lea un archivo **JSON**, aplique operaciones de filtrado y agregación de datos, e incluya un manejo de errores robusto para excepciones de archivo y formato.

### 3. Funciones y Programación "Pythonic"
* **Laboratorio:** 
  * Implementar un decorador de reintentos con estrategia de *backoff*.
  * Crear un generador para procesamiento por lotes (*batches*).
  * Construir un *context manager* para la medición de tiempos de ejecución (*timing*).

### 4. Objetos y Modelos de Datos
* **Laboratorio:** 
  * Definir una `dataclass` llamada `Order` con cálculos derivados y métodos de comparación.
  * Crear modelos con **Pydantic** (`OrderIn` y `OrderOut`) para validación/serialización y transformación hacia la entidad del dominio.

### 5. Tipado Estático Opcional y Calidad
* **Laboratorio:** 
  * Añadir anotaciones de tipos (*type hints*) al código previo.
  * Ejecutar análisis estático mediante `mypy` y linter con `ruff`.
  * Configurar e integrar los chequeos automáticos en `pre-commit`.

### 6. Librería Estándar y E/S
* **Laboratorio:** 
  * Realizar la ingesta de un archivo **CSV**, calcular métricas y exportar los resultados a formato **JSON**.
  * Configurar un sistema de **logging** estructurado utilizando distintos niveles de severidad.

### 7. HTTP y Consumo de APIs (Smocker)
* **Laboratorio:** 
  * Construir un cliente HTTP utilizando `httpx` que incluya políticas de reintentos y *timeouts*.
  * Implementar la descarga de archivos a disco mediante *streaming* de respuestas para un uso eficiente de memoria.

---

## 🟡 Intermediate Level

### 8. Acceso a Datos y ORM
* **Laboratorio:** 
  * Definir modelos relacionales `User`, `Order` y `OrderItem` mediante **SQLAlchemy**.
  * Implementar operaciones CRUD básicas y gestionar migraciones de base de datos con **Alembic**.
  * Ejecutar pruebas automatizadas utilizando una base de datos SQLite en memoria.

### 9. APIs Web con FastAPI (Automatización)
* **Laboratorio:** 
  * Desarrollar un CRUD completo para `Orders` con validación mediante schemas Pydantic.
  * Implementar un sistema de autenticación básica mediante **JWT**.
  * Diseñar e implementar pruebas de integración de endpoints utilizando `pytest` y una base de datos temporal.

### 10. Pruebas y TDD
* **Laboratorio:** 
  * Implementar una nueva funcionalidad utilizando la metodología **TDD** (*Test-Driven Development*).
  * Añadir pruebas basadas en propiedades (*property-based testing*) utilizando **Hypothesis**.
  * Generar un reporte de cobertura de código.

### 11. Concurrencia y Rendimiento
* **Laboratorio:** 
  * Desarrollar un cliente concurrente (*Fetcher*) usando `httpx.AsyncClient` y limitar la concurrencia mediante un `asyncio.Semaphore`.
  * Comparar el rendimiento frente a una versión síncrona.
  * Implementar procesamiento de tareas intensivas en CPU (*CPU-bound*) utilizando `ProcessPoolExecutor`.

### 12. Principios SOLID Aplicados en Python
* **Laboratorio:** 
  * Refactorizar un servicio para desacoplarlo mediante un puerto (`Protocol`).
  * Implementar adaptadores para almacenamiento en memoria y en base de datos SQL.
  * Verificar el cumplimiento del Principio de Sustitución de Liskov (LSP).

### 13. Patrones de Diseño
* **Laboratorio:** 
  * Implementar el patrón **Strategy** para la simulación/cálculo de precios.
  * Crear un **Decorator** de almacenamiento en caché.
  * Desarrollar un **Adapter** para la integración con un proveedor externo.
  * Validar los patrones mediante suite de pruebas con `pytest`.

### 14. Ciencia de Datos
* **Laboratorio:** 
  * Cargar y limpiar un conjunto de datos CSV utilizando **Pandas**.
  * Entrenar un modelo de clasificación con **scikit-learn**.
  * Serializar el modelo entrenado con `joblib` y construir un script para ejecutar inferencias básicas.

### 15. Arquitectura Hexagonal (Puertos y Adaptadores)
* **Laboratorio:** 
  * Implementar el caso de uso `CreateOrder` conectándolo a un puerto de repositorio.
  * Crear adaptadores de repositorio en memoria y con **SQLAlchemy**.
  * Implementar un adaptador para notificaciones HTTP simuladas y escribir pruebas de contrato.

---

## 🔴 Advanced Level

### 16. Arquitectura Limpia
* **Laboratorio:** 
  * Reestructurar el servicio de `Orders` siguiendo los principios de Arquitectura Limpia (*Clean Architecture*).
  * Introducir los patrones **Unit of Work** (UoW) y **Presenter**.
  * Publicar y manejar el evento de dominio `OrderCreated` en la capa de aplicación.

### 17. Empaquetado, Distribución y CI/CD
* **Laboratorio:** 
  * Generar el empaquetado del proyecto en formato *wheel*.
  * Crear un `Dockerfile` optimizado en múltiples etapas (*multistage*).
  * Configurar un pipeline de integración continua (CI) que ejecute *linting*, *type-checking*, ejecución de pruebas y construcción de la imagen de Docker para su publicación en un *registry*.

### 18. CLI y Automatización
* **Laboratorio:** 
  * Desarrollar una interfaz de línea de comandos (CLI) con **Typer** para la gestión de órdenes (crear, listar, eliminar) que consuma la API.
  * Configurar un *entry point* ejecutable dentro del paquete Python.

### 19. Seguridad y Mantenimiento
* **Laboratorio:** 
  * Integrar `pydantic-settings` para la gestión segura de variables de entorno y secretos.
  * Ejecutar auditorías de seguridad en dependencias con `pip-audit` / `safety` y corregir vulnerabilidades encontradas.
  * Endurecer el contenedor Docker configurándolo para ejecutarse con un usuario sin privilegios (*non-root*) y permisos mínimos.

### 20. Interoperabilidad y Ecosistema Mixto (Opcional)
* **Laboratorio:** 
  * Definir contratos de servicio mediante archivos `.proto` para `Orders` y generar código de stubs.
  * Implementar un servidor y cliente **gRPC**.
  * Publicar el evento `OrderCreated` hacia un broker de mensajería como **RabbitMQ** o **Redis**.

---

## 🏆 Proyecto Final Integrador (Arquitectura Hexagonal/Limpia)
* **Laboratorio / Entregable Principal:**
  * **Core del Servicio:** Construcción de un servicio completo de `Orders` aplicando Arquitectura Hexagonal/Limpia (división explícita en capas: *Dominio*, *Aplicación* e *Infraestructura*).
  * **API & Seguridad:** Exposición de una API en **FastAPI** autenticada y documentada (OpenAPI).
  * **Persistencia & Migraciones:** Integración con base de datos mediante ORM y migraciones con **Alembic**.
  * **Calidad de Código & Pruebas:** Cobertura con pruebas unitarias, de contrato, de integración y *end-to-end* (E2E), junto con tipado estático y linters en regla.
  * **Contenerización & Delivery:** `Dockerfile` multistage, pipeline de CI/CD automatizado y auditoría de seguridad en dependencias.
  * **Documentación:** Generación del `README.md`, diagramas explicativos y evidencias de cumplimiento de rúbrica.
README.md
Mostrando README.md.
