#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DB_NAME="${DB_NAME:-secure_login_db}"
DB_USER="${DB_USER:-secure_user}"
DB_PASS="${DB_PASS:-}"

if [[ -z "$DB_PASS" ]]; then
  DB_PASS="$(python3 - <<'PY'
import secrets
alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
print(''.join(secrets.choice(alphabet) for _ in range(24)))
PY
)"
fi

gen_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
}

set_env_var() {
  local key="$1"
  local value="$2"
  if grep -qE "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}

echo "[1/6] Checking Python venv"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "[2/6] Installing MySQL server/client (requires sudo password)"
if ! command -v mysql >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y mysql-server mysql-client
fi

echo "[3/6] Starting MySQL service"
sudo systemctl enable --now mysql

if ! sudo mysqladmin ping >/dev/null 2>&1; then
  echo "MySQL server is not reachable even after start."
  exit 1
fi

echo "[4/6] Creating database and app user"
sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "[5/6] Updating .env for real MySQL"
if [[ ! -f .env ]]; then
  cp .env.example .env
fi

SECRET_KEY_VALUE="$(gen_secret)"
JWT_SECRET_KEY_VALUE="$(gen_secret)"
set_env_var "FLASK_ENV" "development"
set_env_var "FLASK_DEBUG" "0"
set_env_var "DATABASE_URL" "mysql+pymysql://${DB_USER}:${DB_PASS}@localhost/${DB_NAME}"
set_env_var "SECRET_KEY" "$SECRET_KEY_VALUE"
set_env_var "JWT_SECRET_KEY" "$JWT_SECRET_KEY_VALUE"
set_env_var "TURNSTILE_ENABLED" "false"
set_env_var "JWT_COOKIE_SECURE" "false"
set_env_var "ALLOW_ADMIN_SELF_REGISTRATION" "true"

echo "[6/6] Running migrations"
export FLASK_APP=run.py
flask db upgrade

echo
echo "Real MySQL setup complete."
echo "Database: ${DB_NAME}"
echo "User: ${DB_USER}"
echo "Password: ${DB_PASS}"
echo
echo "Now run:"
echo "source .venv/bin/activate && python run.py"
