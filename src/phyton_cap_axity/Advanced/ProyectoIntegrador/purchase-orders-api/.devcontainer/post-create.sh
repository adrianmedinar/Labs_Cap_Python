#!/usr/bin/env bash
# Se ejecuta automáticamente una vez al crear el Codespace/devcontainer.
set -euo pipefail

echo "==> Creando entorno virtual..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> Instalando el proyecto en modo editable + dependencias de desarrollo..."
pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet

# Ver docs/audit/README.md: pin necesario por incompatibilidad conocida
# entre passlib 1.7.4 y bcrypt>=4.1.
pip install "bcrypt>=4.0.1,<4.1.0" --force-reinstall --quiet

echo "==> Preparando archivo .env de desarrollo (si no existe)..."
if [ ! -f .env ]; then
  cp .env.example .env
  # SQLite por defecto en Codespaces: cero configuración adicional.
  sed -i 's|^DATABASE_URL=.*|DATABASE_URL=sqlite+aiosqlite:///./purchase_orders.db|' .env
  sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$(openssl rand -hex 32)|" .env
fi

echo "==> Aplicando migraciones (SQLite local)..."
set -a; source .env; set +a
alembic upgrade head

echo ""
echo "✅ Entorno listo. Para empezar:"
echo "   source .venv/bin/activate"
echo "   uvicorn purchase_orders.api.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "   Documentación interactiva en: http://localhost:8000/docs"
echo "   Ejecutar pruebas:            pytest"
