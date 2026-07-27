"""Pruebas de CONTRATO: validan que la API cumple su contrato HTTP público
(esquema OpenAPI válido, forma de las respuestas, códigos de estado, y
compatibilidad con el flujo estándar OAuth2). A diferencia de las pruebas
E2E (que verifican comportamiento de negocio de punta a punta), estas
pruebas se enfocan en la SUPERFICIE de la API como contrato para
consumidores externos (frontend, otros servicios, SDKs generados).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.contract


class TestOpenApiSchema:
    async def test_openapi_json_disponible_y_valido(self, client: AsyncClient) -> None:
        response = await client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert schema["openapi"].startswith("3.")
        assert schema["info"]["title"] == "Purchase Orders API"

    async def test_todos_los_endpoints_de_negocio_documentados(
        self, client: AsyncClient
    ) -> None:
        schema = (await client.get("/openapi.json")).json()
        paths = schema["paths"]

        expected_paths = [
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/suppliers",
            "/api/v1/suppliers/{supplier_id}",
            "/api/v1/purchase-orders",
            "/api/v1/purchase-orders/{order_id}",
            "/api/v1/purchase-orders/{order_id}/submit",
            "/api/v1/purchase-orders/{order_id}/approve",
            "/api/v1/purchase-orders/{order_id}/reject",
            "/api/v1/purchase-orders/{order_id}/send-to-supplier",
            "/api/v1/purchase-orders/{order_id}/confirm-receipt",
            "/api/v1/purchase-orders/{order_id}/close",
            "/api/v1/purchase-orders/{order_id}/cancel",
        ]
        for path in expected_paths:
            assert path in paths, f"Endpoint faltante en el contrato: {path}"

    async def test_endpoints_protegidos_declaran_seguridad_bearer(
        self, client: AsyncClient
    ) -> None:
        schema = (await client.get("/openapi.json")).json()
        create_supplier_op = schema["paths"]["/api/v1/suppliers"]["post"]
        assert "security" in create_supplier_op

    async def test_docs_y_redoc_disponibles(self, client: AsyncClient) -> None:
        assert (await client.get("/docs")).status_code == 200
        assert (await client.get("/redoc")).status_code == 200


class TestContratoRespuestas:
    async def test_health_check_forma_esperada(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"status", "environment"}

    async def test_error_400_tiene_forma_estandar(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        headers = await auth_headers_factory(role="admin")
        # Proveedor inexistente -> 404 con forma {"detail": "..."}
        import uuid

        response = await client.post(
            "/api/v1/purchase-orders",
            json={
                "supplier_id": str(uuid.uuid4()),
                "currency": "MXN",
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
        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], str)

    async def test_error_422_en_validacion_de_entrada(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        headers = await auth_headers_factory(role="admin")
        response = await client.post(
            "/api/v1/suppliers",
            json={"name": "", "tax_id": "", "email": "no-es-un-email"},
            headers=headers,
        )
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body  # forma estándar de FastAPI para errores de validación

    async def test_purchase_order_response_tiene_todos_los_campos_del_contrato(
        self, client: AsyncClient, auth_headers_factory: Callable
    ) -> None:
        headers = await auth_headers_factory(role="admin")
        supplier_resp = await client.post(
            "/api/v1/suppliers",
            json={"name": "Acme", "tax_id": "RFC-CT1", "email": "v@acme.com"},
            headers=headers,
        )
        supplier_id = supplier_resp.json()["id"]

        response = await client.post(
            "/api/v1/purchase-orders",
            json={
                "supplier_id": supplier_id,
                "currency": "MXN",
                "line_items": [
                    {
                        "sku": "SKU-1",
                        "description": "Item",
                        "quantity": 1,
                        "unit_price": "10.00",
                    }
                ],
            },
            headers=headers,
        )
        body = response.json()
        expected_fields = {
            "id",
            "supplier_id",
            "status",
            "currency",
            "requested_by",
            "approved_by",
            "rejection_reason",
            "line_items",
            "total",
            "created_at",
            "updated_at",
            "version",
        }
        assert expected_fields.issubset(body.keys())
        assert body["line_items"][0].keys() == {
            "sku",
            "description",
            "quantity",
            "unit_price",
            "subtotal",
        }

    async def test_token_login_es_compatible_con_oauth2_password_flow(
        self, client: AsyncClient
    ) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "contractuser",
                "email": "contract@corp.com",
                "password": "secret123",
                "role": "requester",
            },
        )
        # El contrato exige application/x-www-form-urlencoded, no JSON
        # (estándar OAuth2 Password Flow, consumido por Swagger 'Authorize').
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "contractuser", "password": "secret123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"access_token", "token_type"}
        assert body["token_type"] == "bearer"
