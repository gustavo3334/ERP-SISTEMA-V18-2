#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Ambiente nao instalado. Execute ./INSTALAR-MAC.command primeiro."
  exit 1
fi
source .venv/bin/activate
PYTHONPATH=. pytest -q
