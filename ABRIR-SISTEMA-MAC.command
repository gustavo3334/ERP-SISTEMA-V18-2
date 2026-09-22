#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Ambiente nao instalado. Execute ./INSTALAR-MAC.command primeiro."
  exit 1
fi
source .venv/bin/activate
(open "http://127.0.0.1:8000" >/dev/null 2>&1 &) || true
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
