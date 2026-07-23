"""Pruebas E2E: ejercitan la API completa vía HTTP (sin mocks, con la app
FastAPI real montada sobre `httpx.ASGITransport` y una base de datos
SQLite real). Verifican flujos de NEGOCIO de punta a punta, tal como los
viviría un consumidor real de la API.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.e2e


async def _create_supplier(client: AsyncClient, headers: dict) -> str:
    response = await client.post(
        "/api/v1/suppliers",
        json={
            "name": "Acme Corp",
            "tax_id": f"RFC-{uuid.uuid4().hex[:8]}",
            "email": "v@acme.com",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_order(
    client: AsyncClient, headers: dict, supplier_id: str, unit_price: str = "1500.00"
) -> dict:
    response = await client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "currency": "USD",
            "line_items": [
                {
                    "sku": "SKU-1",
                    "description": "Laptop",
                    "quantity": 2,
                    "unit_price": unit_price,
                }
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


class TestFlujoCompletoDeAprobacion:
    async def test_ciclo_de_vida_completo_draft_hasta_closed(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        requester_headers = await auth_headers_factory(role="requester")
        approver_headers = await auth_headers_factory(role="approver_senior")

        supplier_id = await _create_supplier(client, requester_headers)
        order = await _create_order(client, requester_headers, supplier_id)
        order_id = order["id"]
        assert order["status"] == "DRAFT"
        assert order["total"] == "3000.00"

        response = await client.post(
            f"/api/v1/purchase-orders/{order_id}/submit", headers=requester_headers
        )
        assert response.json()["status"] == "PENDING_APPROVAL"

        response = await client.post(
            f"/api/v1/purchase-orders/{order_id}/approve", headers=approver_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"
        assert response.json()["approved_by"] is not None

        response = await client.post(
            f"/api/v1/purchase-orders/{order_id}/send-to-supplier",
            headers=requester_headers,
        )
        assert response.json()["status"] == "SENT_TO_SUPPLIER"

        response = await client.post(
            f"/api/v1/purchase-orders/{order_id}/confirm-receipt",
            headers=requester_headers,
        )
        assert response.json()["status"] == "RECEIVED"

        response = await client.post(
            f"/api/v1/purchase-orders/{order_id}/close", headers=requester_headers
        )
        assert response.json()["status"] == "CLOSED"

        # Verificación final vía GET
        final = await client.get(
            f"/api/v1/purchase-orders/{order_id}", headers=requester_headers
        )
        assert final.json()["status"] == "CLOSED"
        assert final.json()["version"] == 6  # 1 (create) + 5 transiciones

    async def test_flujo_de_rechazo(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        requester_headers = await auth_headers_factory(role="requester")
        approver_headers = await auth_headers_factory(role="approver_senior")

        supplier_id = await _create_supplier(client, requester_headers)
        order = await _create_order(client, requester_headers, supplier_id)

        await client.post(
            f"/api/v1/purchase-orders/{order['id']}/submit", headers=requester_headers
        )
        response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/reject",
            json={"reason": "Precio fuera de mercado"},
            headers=approver_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"
        assert response.json()["rejection_reason"] == "Precio fuera de mercado"

    async def test_flujo_de_cancelacion_desde_draft(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        headers = await auth_headers_factory(role="requester")
        supplier_id = await _create_supplier(client, headers)
        order = await _create_order(client, headers, supplier_id)

        response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/cancel", headers=headers
        )
        assert response.json()["status"] == "CANCELLED"


class TestControlDeAcceso:
    async def test_usuario_sin_rol_de_aprobador_no_puede_aprobar(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        requester_headers = await auth_headers_factory(role="requester")
        supplier_id = await _create_supplier(client, requester_headers)
        order = await _create_order(client, requester_headers, supplier_id)
        await client.post(
            f"/api/v1/purchase-orders/{order['id']}/submit", headers=requester_headers
        )

        response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/approve", headers=requester_headers
        )
        assert response.status_code == 403

    async def test_aprobador_junior_no_puede_aprobar_montos_altos(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        requester_headers = await auth_headers_factory(role="requester")
        junior_headers = await auth_headers_factory(role="approver_junior")
        supplier_id = await _create_supplier(client, requester_headers)

        order = await _create_order(
            client, requester_headers, supplier_id, unit_price="999999.00"
        )
        await client.post(
            f"/api/v1/purchase-orders/{order['id']}/submit", headers=requester_headers
        )

        response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/approve", headers=junior_headers
        )
        assert response.status_code == 403

    async def test_endpoints_requieren_autenticacion(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/purchase-orders")
        assert response.status_code == 401

    async def test_token_invalido_es_rechazado(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/purchase-orders",
            headers={"Authorization": "Bearer token-invalido"},
        )
        assert response.status_code == 401


class TestReglasDeNegocioViaApi:
    async def test_no_se_puede_saltar_estados(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        headers = await auth_headers_factory(role="approver_senior")
        supplier_id = await _create_supplier(client, headers)
        order = await _create_order(client, headers, supplier_id)

        # Intentar aprobar directamente desde DRAFT (sin submit) -> 409
        response = await client.post(
            f"/api/v1/purchase-orders/{order['id']}/approve", headers=headers
        )
        assert response.status_code == 409

    async def test_no_se_puede_crear_orden_con_proveedor_inexistente(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        headers = await auth_headers_factory(role="requester")
        response = await client.post(
            "/api/v1/purchase-orders",
            json={
                "supplier_id": str(uuid.uuid4()),
                "currency": "USD",
                "line_items": [
                    {
                        "sku": "SKU-1",
                        "description": "Item",
                        "quantity": 1,
                        "unit_price": "1.00",
                    }
                ],
            },
            headers=headers,
        )
        assert response.status_code == 404

    async def test_listado_con_paginacion(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        headers = await auth_headers_factory(role="requester")
        supplier_id = await _create_supplier(client, headers)
        for _ in range(3):
            await _create_order(client, headers, supplier_id)

        response = await client.get(
            "/api/v1/purchase-orders", params={"limit": 2, "offset": 0}, headers=headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 2
