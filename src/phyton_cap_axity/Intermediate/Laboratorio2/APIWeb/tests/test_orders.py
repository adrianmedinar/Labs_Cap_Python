import pytest

pytestmark = pytest.mark.asyncio


async def test_crear_orden(client, auth_headers):
    resp = await client.post(
        "/api/v1/orders",
        json={"item": "Teclado mecánico", "quantity": 2, "unit_price": 45.5},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["item"] == "Teclado mecánico"
    assert body["status"] == "pending"
    assert body["total_price"] == 91.0


async def test_crear_orden_cantidad_invalida_falla(client, auth_headers):
    resp = await client.post(
        "/api/v1/orders",
        json={
            "item": "Mouse",
            "quantity": 0,
            "unit_price": 10,
        },  # quantity debe ser > 0
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_crear_orden_precio_negativo_falla(client, auth_headers):
    resp = await client.post(
        "/api/v1/orders",
        json={"item": "Mouse", "quantity": 1, "unit_price": -5},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_listar_ordenes(client, auth_headers):
    for i in range(3):
        await client.post(
            "/api/v1/orders",
            json={"item": f"Item {i}", "quantity": 1, "unit_price": 10},
            headers=auth_headers,
        )
    resp = await client.get("/api/v1/orders", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_obtener_orden_por_id(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/orders",
        json={"item": "Monitor", "quantity": 1, "unit_price": 300},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["item"] == "Monitor"


async def test_obtener_orden_inexistente_404(client, auth_headers):
    resp = await client.get("/api/v1/orders/9999", headers=auth_headers)
    assert resp.status_code == 404


async def test_actualizar_orden_parcial(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/orders",
        json={"item": "Silla", "quantity": 1, "unit_price": 120},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/orders/{order_id}",
        json={"status": "paid", "quantity": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "paid"
    assert body["quantity"] == 2
    assert body["item"] == "Silla"  # no se tocó, PATCH es parcial


async def test_eliminar_orden(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/orders",
        json={"item": "Lámpara", "quantity": 1, "unit_price": 25},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_transicion_de_estado_valida_pending_a_paid(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/orders",
        json={"item": "Audífonos", "quantity": 1, "unit_price": 50},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/orders/{order_id}", json={"status": "paid"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"


async def test_transicion_de_estado_invalida_devuelve_409(client, auth_headers):
    """shipped -> pending no es una transición permitida."""
    create_resp = await client.post(
        "/api/v1/orders",
        json={"item": "Cámara", "quantity": 1, "unit_price": 500},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    # Llevamos la orden hasta 'shipped' (transiciones válidas)
    await client.patch(
        f"/api/v1/orders/{order_id}", json={"status": "paid"}, headers=auth_headers
    )
    await client.patch(
        f"/api/v1/orders/{order_id}", json={"status": "shipped"}, headers=auth_headers
    )

    # Intentamos retroceder: debe fallar
    resp = await client.patch(
        f"/api/v1/orders/{order_id}", json={"status": "pending"}, headers=auth_headers
    )
    assert resp.status_code == 409

    # Y el estado real no debe haber cambiado
    check = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert check.json()["status"] == "shipped"


async def test_no_se_puede_modificar_orden_cancelada(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/orders",
        json={"item": "Bicicleta", "quantity": 1, "unit_price": 800},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    await client.patch(
        f"/api/v1/orders/{order_id}", json={"status": "cancelled"}, headers=auth_headers
    )

    resp = await client.patch(
        f"/api/v1/orders/{order_id}", json={"status": "paid"}, headers=auth_headers
    )
    assert resp.status_code == 409


async def test_ordenes_aisladas_entre_usuarios(client, auth_headers):
    """Un usuario no debe poder ver/editar órdenes de otro (multi-tenant básico)."""
    # Orden del usuario A (auth_headers)
    create_resp = await client.post(
        "/api/v1/orders",
        json={"item": "Secreto de A", "quantity": 1, "unit_price": 10},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    # Usuario B se registra y logea
    await client.post(
        "/api/v1/auth/register",
        json={"email": "userb@example.com", "password": "ClaveSegura123"},
    )
    login_b = await client.post(
        "/api/v1/auth/login",
        data={"username": "userb@example.com", "password": "ClaveSegura123"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    # B no debe poder ver la orden de A
    resp = await client.get(f"/api/v1/orders/{order_id}", headers=headers_b)
    assert resp.status_code == 404
