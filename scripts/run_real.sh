#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo ".env not found. Run scripts/setup_real_mysql.sh first."
  exit 1
fi

source .venv/bin/activate
export FLASK_APP=run.py
python run.py
