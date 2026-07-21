import pytest

pytestmark = pytest.mark.asyncio


async def test_register_success(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "nuevo@example.com", "password": "ClaveSegura123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "nuevo@example.com"
    assert "hashed_password" not in body  # nunca se filtra el hash


async def test_register_duplicado_falla(client):
    payload = {"email": "dup@example.com", "password": "ClaveSegura123"}
    r1 = await client.post("/api/v1/auth/register", json=payload)
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 400


async def test_register_password_corta_falla_validacion(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "corta@example.com", "password": "123"},
    )
    assert resp.status_code == 422  # violación de min_length en el schema


async def test_login_exitoso_devuelve_jwt(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "ClaveSegura123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "ClaveSegura123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 10


async def test_login_password_incorrecta_falla(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpass@example.com", "password": "ClaveSegura123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "wrongpass@example.com", "password": "incorrecta"},
    )
    assert resp.status_code == 401


async def test_endpoint_protegido_sin_token_falla(client):
    resp = await client.get("/api/v1/orders")
    assert resp.status_code == 401
