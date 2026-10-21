"""Fácil Pedido Unificado: ERP 18.2 em / e Comercial V5 em /comercial/.

Montagens ordenadas: a rota catch-all do ERP não engole o Comercial.
Ambos executam seus respectivos lifespan hooks. Não copia tabelas e não
altera URLs dos bancos: ERP usa DATABASE_URL; Comercial, CATALOG_DATABASE_URL.
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

if os.getenv("COMBINED_DEPLOYMENT", "").strip().lower() != "true":
    raise RuntimeError("Para usar combined_app, configure COMBINED_DEPLOYMENT=true")

ROOT = Path(__file__).resolve().parent
COMMERCIAL_ROOT = ROOT / "commercial_v5"
if not (COMMERCIAL_ROOT / "gateway" / "main.py").is_file():
    raise RuntimeError("Pasta commercial_v5 não instalada. Execute preparar-unificado.ps1")
sys.path.insert(0, str(COMMERCIAL_ROOT))

from app.main import app as erp_app  # noqa: E402
from gateway.main import app as commercial_app  # noqa: E402

@asynccontextmanager
async def combined_lifespan(_app: FastAPI):
    # Starlette não executa automaticamente lifespan de subapps montados.
    async with erp_app.router.lifespan_context(erp_app):
        async with commercial_app.router.lifespan_context(commercial_app):
            yield

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=combined_lifespan)

@app.get("/comercial", include_in_schema=False)
def go_commercial():
    return RedirectResponse(url="/comercial/", status_code=307)

# Ordem fundamental: /comercial/ deve vir antes do ERP montado em /.
app.mount("/comercial", commercial_app)
app.mount("/", erp_app)
