# Diagramas del Proyecto

Todos los diagramas están escritos en [Mermaid](https://mermaid.js.org/) y se renderizan automáticamente al ver este archivo en GitHub, GitLab, o el propio VS Code (extensión *Markdown Preview Mermaid Support*).

El código fuente de cada diagrama también vive en su propio archivo `.mmd` en esta carpeta, por si necesitas editarlo o pegarlo directamente en el [Mermaid Live Editor](https://mermaid.live/) para exportarlo como PNG/SVG de alta resolución.

> **Validación realizada**: la gramática de `er-diagram.mmd` y `sequence-create-approve-flow.mmd` fue verificada programáticamente con el parser real de `mermaid` (Node.js). Los diagramas de tipo `flowchart` y `stateDiagram` (`architecture-hexagonal`, `ci-cd-pipeline`, `state-machine-purchase-order`) no pudieron validarse por el mismo medio en este entorno (limitación de `DOMPurify` bajo `jsdom` sin navegador real disponible), por lo que se revisaron manualmente línea por línea; se corrigieron dos problemas reales encontrados en esa revisión (un `\n` literal mal usado y símbolos `<`/`>` sueltos que Mermaid podría confundir con HTML dentro de una nota).

---

## 1. Arquitectura Hexagonal (capas y dirección de dependencias)

*Fuente: [`architecture-hexagonal.mmd`](architecture-hexagonal.mmd)*

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontSize': '16px'}}}%%
flowchart TB
    subgraph API["🌐 API — FastAPI"]
        direction TB
        A1["routers/<br/>auth · suppliers · purchase-orders"]
        A2["schemas/<br/>Pydantic request/response"]
        A3["dependencies.py<br/>DI + JWT (OAuth2PasswordBearer)"]
        A4["error_handlers.py<br/>excepción → HTTP"]
    end

    subgraph APP["⚙️ Aplicación — Casos de Uso"]
        direction TB
        U1["use_cases/<br/>Create, Submit, Approve, Reject,<br/>Send, ConfirmReceipt, Close, Cancel,<br/>Login, RegisterUser, Queries"]
        U2["dtos/<br/>Commands & Results (dataclasses)"]
        U3["mappers.py"]
    end

    subgraph DOM["💎 Dominio — Núcleo de Negocio (puro)"]
        direction TB
        D1["entities/<br/>PurchaseOrder · Supplier · User"]
        D2["value_objects/<br/>Money · LineItem · PurchaseOrderStatus"]
        D3["services/<br/>ApprovalPolicy"]
        D4["ports/ (interfaces)<br/>Repositories · PasswordHasher ·<br/>TokenProvider · UnitOfWork"]
        D5["exceptions/"]
    end

    subgraph INFRA["🔌 Infraestructura — Adaptadores"]
        direction TB
        I1["db/<br/>SQLAlchemy models · repos · UoW"]
        I2["security/<br/>JwtTokenProvider (PyJWT)<br/>BcryptPasswordHasher (passlib)"]
        I3["container.py<br/>Composition Root"]
        I4["config.py<br/>Settings (pydantic-settings)"]
    end

    API -->|"invoca"| APP
    APP -->|"depende de<br/>(interfaces)"| D4
    I1 -.->|"implementa"| D4
    I2 -.->|"implementa"| D4
    I3 -.->|"ensambla e inyecta"| A3
    I3 -.->|"ensambla e inyecta"| U1

    style DOM fill:#e8f4ea,stroke:#2e7d32,stroke-width:2px
    style APP fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style API fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    style INFRA fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
```

> Las flechas continuas indican invocación/uso; las punteadas indican 'implementa la interfaz de'. Nótese que **Infraestructura** es la única capa que conoce simultáneamente al Dominio (para implementar sus puertos) y a la API (para inyectarse en ella vía el `Container`).

---

## 2. Máquina de Estados de la Orden de Compra

*Fuente: [`state-machine-purchase-order.mmd`](state-machine-purchase-order.mmd)*

```mermaid
%%{init: {'theme': 'base'}}%%
stateDiagram-v2
    [*] --> DRAFT: create()

    DRAFT --> PENDING_APPROVAL: submit()
    DRAFT --> CANCELLED: cancel()

    PENDING_APPROVAL --> APPROVED: approve() [monto dentro del limite del rol]
    PENDING_APPROVAL --> REJECTED: reject(reason)
    PENDING_APPROVAL --> CANCELLED: cancel()

    APPROVED --> SENT_TO_SUPPLIER: send_to_supplier()
    APPROVED --> CANCELLED: cancel()

    SENT_TO_SUPPLIER --> RECEIVED: confirm_receipt()

    RECEIVED --> CLOSED: close()

    REJECTED --> [*]
    CANCELLED --> [*]
    CLOSED --> [*]

    note right of DRAFT
        Única fase editable:
        add_line_item / remove_line_item
        No puede quedar vacía (EmptyPurchaseOrderError)
    end note

    note right of PENDING_APPROVAL
        ApprovalPolicy valida el limite
        de monto autorizable por rol, de menor a mayor:
        approver_junior, approver_senior, admin
        Si excede -> ApprovalThresholdExceededError
    end note
```

> Implementada en `domain/value_objects/purchase_order_status.py`. Cualquier transición no dibujada aquí es inválida y lanza `InvalidPurchaseOrderStateError` (HTTP 409).

---

## 3. Secuencia: Login → Crear Orden → Aprobar

*Fuente: [`sequence-create-approve-flow.mmd`](sequence-create-approve-flow.mmd)*

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    actor Cliente
    participant API as FastAPI Router
    participant Dep as Dependencies<br/>(JWT / Roles)
    participant UC as Casos de Uso
    participant Dom as Dominio<br/>(PurchaseOrder / ApprovalPolicy)
    participant UoW as UnitOfWork
    participant DB as PostgreSQL

    Cliente->>API: POST /auth/login (username, password)
    API->>UC: LoginUseCase.execute()
    UC->>UoW: users.get_by_username()
    UoW->>DB: SELECT
    DB-->>UoW: User
    UC->>UC: password_hasher.verify()
    UC->>UC: token_provider.create_access_token()
    UC-->>API: TokenResult(access_token)
    API-->>Cliente: 200 {access_token, token_type}

    Cliente->>API: POST /purchase-orders<br/>Authorization: Bearer <token>
    API->>Dep: get_current_user(token)
    Dep->>Dep: token_provider.decode()
    Dep-->>API: TokenPayload(username, role)
    API->>UC: CreatePurchaseOrderUseCase.execute()
    UC->>UoW: suppliers.get_by_id()
    UoW->>DB: SELECT
    UC->>Dom: PurchaseOrder.create(line_items)
    Dom-->>UC: PurchaseOrder (DRAFT)
    UC->>UoW: purchase_orders.add() + commit()
    UoW->>DB: INSERT
    UC-->>API: PurchaseOrderResult
    API-->>Cliente: 201 Created

    Cliente->>API: POST /purchase-orders/{id}/submit
    API->>UC: SubmitPurchaseOrderUseCase.execute()
    UC->>UoW: purchase_orders.get_by_id()
    UoW->>DB: SELECT
    UC->>Dom: order.submit()
    Dom-->>UC: PENDING_APPROVAL
    UC->>UoW: purchase_orders.update() + commit()
    UoW->>DB: UPDATE
    UC-->>API: PurchaseOrderResult
    API-->>Cliente: 200 OK

    Cliente->>API: POST /purchase-orders/{id}/approve<br/>(rol: approver_senior)
    API->>Dep: require_roles("approver_junior","approver_senior","admin")
    Dep-->>API: OK (rol permitido)
    API->>UC: ApprovePurchaseOrderUseCase.execute()
    UC->>UoW: purchase_orders.get_by_id()
    UC->>Dom: ApprovalPolicy.max_approvable_amount(role)
    Dom-->>UC: Money(limit)
    UC->>Dom: order.approve(approved_by, limit)
    alt total > limit
        Dom-->>UC: raise ApprovalThresholdExceededError
        UC-->>API: excepción de dominio
        API-->>Cliente: 403 Forbidden
    else total <= limit
        Dom-->>UC: APPROVED
        UC->>UoW: purchase_orders.update() + commit()
        UoW->>DB: UPDATE (version++)
        UC-->>API: PurchaseOrderResult
        API-->>Cliente: 200 OK
    end
```

> Ilustra cómo la API traduce JWT a `TokenPayload`, cómo los casos de uso orquestan puertos vía `UnitOfWork`, y cómo `ApprovalPolicy` (servicio de dominio) decide si el monto está dentro del límite del rol.

---

## 4. Modelo de Datos (Entidad-Relación)

*Fuente: [`er-diagram.mmd`](er-diagram.mmd)*

```mermaid
%%{init: {'theme': 'base'}}%%
erDiagram
    SUPPLIERS ||--o{ PURCHASE_ORDERS : "provee"
    PURCHASE_ORDERS ||--|{ PURCHASE_ORDER_LINE_ITEMS : "contiene"
    USERS ||--o{ PURCHASE_ORDERS : "solicita / aprueba (por username, no FK)"

    SUPPLIERS {
        uuid id PK
        string name
        string tax_id UK
        string email
        bool is_active
    }

    USERS {
        uuid id PK
        string username UK
        string email
        string hashed_password
        string role
        bool is_active
    }

    PURCHASE_ORDERS {
        uuid id PK
        uuid supplier_id FK
        string status
        string currency
        string requested_by
        string approved_by
        string rejection_reason
        datetime created_at
        datetime updated_at
        int version "control de concurrencia optimista"
    }

    PURCHASE_ORDER_LINE_ITEMS {
        uuid id PK
        uuid purchase_order_id FK
        string sku
        string description
        int quantity
        numeric unit_price
    }
```

> `requested_by` / `approved_by` se guardan como `username` (string), no como *foreign key* a `users`, para mantener el agregado `PurchaseOrder` desacoplado del ciclo de vida de las cuentas de usuario.

---

## 5. Pipeline de CI/CD

*Fuente: [`ci-cd-pipeline.mmd`](ci-cd-pipeline.mmd)*

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    Push["git push / Pull Request<br/>(o cron semanal)"] --> Lint & Type & Test & Audit & Mig

    subgraph Paralelo["Jobs en paralelo"]
        Lint["lint<br/>ruff check + format --check"]
        Type["typecheck<br/>mypy src"]
        Test["test<br/>pytest (115 pruebas) + cobertura"]
        Audit["dependency-audit<br/>pip-audit"]
        Mig["migration-check<br/>alembic upgrade/downgrade/upgrade"]
    end

    Lint --> Build
    Type --> Build
    Test --> Build
    Audit --> Build
    Mig --> Build

    Build["build<br/>python -m build (sdist+wheel)<br/>docker build (sin publicar)"]

    Build --> Gate{"¿rama == main<br/>y push directo?"}
    Gate -->|"sí"| Publish["publish-image<br/>docker push → GHCR"]
    Gate -->|"no (PR)"| End1["Fin: solo validación"]

    Test -.->|"artefacto"| Cov["coverage.xml<br/>(30 días)"]
    Audit -.->|"artefacto"| Rep["pip-audit-report.json<br/>(90 días)"]

    style Paralelo fill:#e3f2fd,stroke:#1565c0
    style Build fill:#fff3e0,stroke:#ef6c00
    style Publish fill:#e8f4ea,stroke:#2e7d32
```

> Los 5 jobs de validación corren en paralelo; `build` solo se ejecuta si todos pasan. La publicación de imagen a GHCR solo ocurre en push directo a `main` (no en Pull Requests).

---

## Cómo generar imágenes PNG/SVG a partir de estos diagramas

```bash
# Opción 1: Mermaid CLI (requiere Node.js + Chrome/Chromium disponible)
npm install -g @mermaid-js/mermaid-cli
mmdc -i docs/diagrams/architecture-hexagonal.mmd -o docs/diagrams/architecture-hexagonal.png

# Opción 2: pegar el contenido del .mmd en https://mermaid.live/
# y usar el botón 'Actions -> Export image'
```
