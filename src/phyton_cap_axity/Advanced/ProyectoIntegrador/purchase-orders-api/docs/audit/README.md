# Evidencia de Auditoría de Dependencias

Este documento registra la auditoría de seguridad de dependencias realizada
sobre el proyecto **Purchase Orders API**, ejecutada con
[`pip-audit`](https://github.com/pypa/pip-audit) (usa las bases de datos
**OSV** y **PyPA Advisory Database**).

## Ejecución

```bash
pip-audit --desc -f json -o docs/audit/pip-audit-report.json
pip-audit --desc
```

Esta auditoría también corre automáticamente en **cada push y pull request**
como parte del pipeline de CI (job `dependency-audit` en
`.github/workflows/ci.yml`), y de forma **programada semanalmente**
(`schedule` cron) para detectar CVEs publicados *después* del último cambio
de código, cuando ninguna dependencia nueva se instaló pero sí apareció una
vulnerabilidad nueva sobre una versión ya fijada.

## Hallazgos y remediación (ejecución inicial)

La primera ejecución de auditoría, sobre las dependencias inicialmente
fijadas en `pyproject.toml`, encontró **10 vulnerabilidades conocidas en 2
paquetes**:

| Paquete | Versión auditada | CVE / Advisory | Corregido en | Acción tomada |
|---|---|---|---|---|
| `starlette` (dependencia transitiva de `fastapi`) | 0.46.2 | PYSEC-2026-161 | 1.0.1 | Ver abajo |
| `starlette` | 0.46.2 | PYSEC-2026-248 | 1.3.0 | Ver abajo |
| `starlette` | 0.46.2 | PYSEC-2026-249 | 1.3.1 | Ver abajo |
| `starlette` | 0.46.2 | PYSEC-2026-1941 | 0.47.2 | Ver abajo |
| `starlette` | 0.46.2 | PYSEC-2026-1942 | 0.49.1 | Ver abajo |
| `starlette` | 0.46.2 | PYSEC-2026-2280 | 1.1.0 | Ver abajo |
| `starlette` | 0.46.2 | PYSEC-2026-2281 | 1.1.0 | Ver abajo |
| `pytest` | 8.4.2 | PYSEC-2026-1845 | 9.0.3 | Ver abajo |

### Remediación aplicada

1. **`starlette`**: la versión de `fastapi` inicialmente fijada
   (`>=0.115.0,<0.116.0`) restringía `starlette` a `<0.51.0`, lo que
   impedía llegar a las versiones `1.x` donde se corrigen varios de estos
   CVEs. Se actualizó:
   - `fastapi` → `>=0.139.2,<0.140.0` (esta versión ya no impone tope
     superior a `starlette`, solo `starlette>=0.46.0`).
   - `starlette` → pin explícito `>=1.3.1,<2.0.0` (corrige **todos** los
     CVEs listados arriba).
2. **`pytest`**: actualizado a `>=9.0.3,<10.0.0` (corrige PYSEC-2026-1845).
   Esto requirió además actualizar `pytest-asyncio` a `>=1.4.0,<2.0.0`
   (la versión previamente fijada, `0.24.0`, no era compatible con
   `pytest 9.x` y el resolutor de `pip` rechazaba la instalación).

Tras aplicar estos cambios en `pyproject.toml` y reinstalar
(`pip install -e ".[dev]" --upgrade`), **se re-ejecutó toda la suite de 115
pruebas para confirmar que ninguna de estas actualizaciones (dos de ellas
con cambio de versión mayor) rompió compatibilidad**. Resultado: **115/115
pruebas pasaron, 93.95% de cobertura**, sin cambios de código necesarios más
allá de las versiones en `pyproject.toml`.

## Resultado final

```
$ pip-audit --desc
No known vulnerabilities found
```

✅ **0 vulnerabilidades conocidas** en las dependencias directas y
transitivas del proyecto, al momento de esta auditoría.

## Artefactos de esta auditoría

- [`pip-audit-report.json`](./pip-audit-report.json) — reporte estructurado
  (formato usado por el job de CI para fallar el build si reaparecen
  vulnerabilidades).
- [`pip-audit-report.txt`](./pip-audit-report.txt) — salida legible en texto
  plano.
- [`requirements-freeze-audited.txt`](./requirements-freeze-audited.txt) —
  `pip freeze` exacto del entorno auditado (para trazabilidad/reproducibilidad).

## Política de mantenimiento continuo

- **Dependabot** (`.github/dependabot.yml`) abre PRs automáticos semanales
  para actualizar dependencias de Python y de GitHub Actions.
- El job `dependency-audit` de CI **falla el build** si `pip-audit`
  encuentra una vulnerabilidad conocida sin resolver, evitando que código
  con dependencias inseguras llegue a `main`.
- Cada nueva ejecución de este proceso debe actualizar este documento y sus
  artefactos adjuntos.

---
*Última ejecución: ver fecha de commit de este archivo y de los artefactos
adjuntos en `docs/audit/`.*
