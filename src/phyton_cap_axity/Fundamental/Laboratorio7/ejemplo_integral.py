"""
Prueba de integración: RobustClient contra Smocker.

Requiere que Smocker esté corriendo con el mock de mocks/retry-test.yaml
ya cargado (ver docker-compose.yml + curl -X POST /mocks.

python ejemplo_integral.py
"""

import logging

from robust_http_client import (
    RetryConfig,
    RobustClient,
    TimeoutConfig,
    configure_logging,
)

configure_logging(level=logging.INFO, json_output=False)

with RobustClient(
    base_url="http://localhost:8080",
    timeout=TimeoutConfig(connect=2, read=5),
    retry=RetryConfig(
        max_attempts=4
    ),  # necesita >= 3 intentos para superar los 2 fallos
) as client:
    # El mock responde 503 en las primeras 2 llamadas y 200 en la 3ra.
    # Como max_attempts=4, el cliente debería recuperarse solo, sin que
    # tú tengas que manejar el error manualmente.
    r = client.get("/flaky-recupera")
    print("Resultado final:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["ok"] is True
    print("✅ El cliente se recuperó tras los reintentos automáticos.")

    # Para repetir la prueba hay que resetear Smocker (times_count no se reinicia solo):
    #   curl -X POST http://localhost:8081/reset
    #   curl -X POST http://localhost:8081/mocks -H "Content-Type: application/x-yaml" \
    #        --data-binary @mocks/retry-test.yaml

    # Verificación adicional: consultar cuántas veces Smocker recibió la petición
    import httpx

    admin = httpx.get("http://localhost:8081/history")
    calls = [h for h in admin.json() if h["request"]["path"] == "/flaky-recupera"]
    print(f"Smocker registró {len(calls)} llamadas a /flaky-recupera")
    for i, call in enumerate(calls, 1):
        print(f"  intento {i}: status={call['response']['status']}")
