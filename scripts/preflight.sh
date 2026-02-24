#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Preflight Check =="

if [[ ! -f .env ]]; then
  echo "[FAIL] .env not found"
  exit 1
fi

echo "[OK] .env found"

source .env

if ! command -v mysql >/dev/null 2>&1; then
  echo "[FAIL] mysql command not found"
  exit 1
fi

echo "[OK] mysql client installed"

if ! ss -ltn | grep -q ':3306'; then
  echo "[FAIL] MySQL is not listening on 3306"
  exit 1
fi

echo "[OK] MySQL port is listening"

echo "[INFO] DATABASE_URL=$DATABASE_URL"

source .venv/bin/activate
python3 - <<'PY'
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    db.session.execute(db.text("SELECT 1"))
print("[OK] SQLAlchemy connection successful")
PY

echo "Run next: source .venv/bin/activate && export FLASK_APP=run.py && flask db upgrade"
