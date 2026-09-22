from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app import models_extended  # noqa: F401
from app.api import api_router
from app.bootstrap import bootstrap_database, bootstrap_operational_defaults
from app.config import settings
from app.database import Base, check_database_connection, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialização tolerante a falhas para Vercel/serverless.

    Uma variável incorreta ou uma indisponibilidade temporária do PostgreSQL não
    deve impedir a função de subir. O /api/v1/health passa a informar o problema
    de forma segura, sem expor credenciais.
    """
    app.state.startup_issue = None
    app.state.database_bootstrap_ok = False

    if not settings.is_vercel:
        Path("data").mkdir(exist_ok=True)
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.backup_dir).mkdir(parents=True, exist_ok=True)

    config_errors = settings.runtime_validation_errors()
    if config_errors:
        app.state.startup_issue = "invalid_configuration"
    elif engine is None:
        app.state.startup_issue = "database_engine_unavailable"
    else:
        try:
            if settings.auto_create_tables:
                Base.metadata.create_all(bind=engine)

            database_ok, _ = check_database_connection()
            if database_ok:
                bootstrap_operational_defaults()
                if settings.seed_admin:
                    bootstrap_database()
                app.state.database_bootstrap_ok = True
            else:
                app.state.startup_issue = "database_connection_failed"
        except Exception as exc:
            # Nunca incluímos a mensagem completa: drivers de banco podem
            # carregar detalhes da conexão. O tipo basta para diagnóstico.
            app.state.startup_issue = type(exc).__name__

    yield


app = FastAPI(
    title=settings.app_name,
    version="18.2.0",
    description=(
        "Backend completo do Fácil Pedido ERP: acesso, cadastros, estoque, compras, vendas, "
        "ficha técnica, PCP, produção, entregas, rotas, financeiro, RH, documentos e auditoria."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def production_configuration_guard(request, call_next):
    """Evita erro 500 opaco quando variáveis de produção estão incompletas."""
    path = request.url.path
    diagnostic_paths = {
        f"{settings.api_prefix}/",
        f"{settings.api_prefix}/health",
        f"{settings.api_prefix}/ready",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    if path.startswith(settings.api_prefix) and path not in diagnostic_paths:
        errors = settings.runtime_validation_errors()
        if errors:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Configuração de produção incompleta. Confira as Environment Variables.",
                    "issues": errors,
                },
            )
    return await call_next(request)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_unavailable_handler(request, exc):
    # Não devolve detalhes do driver para evitar exposição acidental de conexão.
    return JSONResponse(
        status_code=503,
        content={"detail": "Banco de dados temporariamente indisponível. Confira DATABASE_URL e tente novamente."},
    )


app.include_router(api_router, prefix=settings.api_prefix)


# Mantém a mesma experiência para execução local/Windows. Na Vercel, os arquivos
# da pasta public/ são servidos pelo CDN e normalmente nem chegam a estas rotas.
frontend_dir = settings.frontend_path
if frontend_dir.exists():
    assets_dir = frontend_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/", include_in_schema=False)
def frontend_root():
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Front-end não encontrado na pasta frontend.")
    return FileResponse(index_file, headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"})


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_spa(full_path: str):
    if full_path.startswith("api/") or full_path in {"docs", "redoc", "openapi.json"}:
        raise HTTPException(status_code=404, detail="Rota não encontrada.")

    requested_file = frontend_dir / full_path
    if requested_file.exists() and requested_file.is_file():
        name = requested_file.name.lower()
        no_cache = name in {"index.html", "config.js", "sw.js", "api-bridge.js", "stock-locations-hotfix.js"}
        headers = {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"} if no_cache else None
        return FileResponse(requested_file, headers=headers)

    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"})
    raise HTTPException(status_code=404, detail="Front-end não encontrado.")
