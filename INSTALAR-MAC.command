#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=========================================="
echo "  FACIL PEDIDO ERP - INSTALACAO NO MAC"
echo "=========================================="
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
mkdir -p data backup storage/uploads
python -m alembic upgrade head
python -m app.seed
echo
echo "Instalacao concluida."
echo "Agora execute: ./ABRIR-SISTEMA-MAC.command"
