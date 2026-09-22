from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.database import check_database_connection, database_runtime

router = APIRouter()


@router.get("/")
def api_root():
    return {
        "name": "Fácil Pedido ERP API",
        "status": "online",
        "version": "18.2.0",
        "docs": "/docs",
    }


@router.get("/health")
def health():
    """Liveness + diagnóstico seguro.

    Este endpoint sempre responde como aplicação quando o FastAPI conseguiu
    inicializar. Assim, erro de configuração ou conexão vira JSON de diagnóstico
    em vez de FUNCTION_INVOCATION_FAILED da Vercel.
    """
    config_errors = settings.runtime_validation_errors()
    database_ok, database_error = check_database_connection()
    runtime = database_runtime()
    issues: list[str] = []
    if config_errors:
        issues.extend(config_errors)
    if not database_ok:
        issues.append(f"Banco indisponível ({database_error or 'erro desconhecido'}).")

    return {
        "status": "ok" if not issues else "degraded",
        "backend": "online",
        "database": "connected" if database_ok else "disconnected",
        "database_provider": runtime.provider,
        "database_pool_mode": runtime.pool_mode,
        "configuration": "ok" if not config_errors else "invalid",
        "issues": issues,
        "version": "18.2.0",
    }


@router.get("/ready")
def ready():
    config_errors = settings.runtime_validation_errors()
    database_ok, database_error = check_database_connection()
    if config_errors or not database_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "configuration": "invalid" if config_errors else "ok",
                "database": "disconnected" if not database_ok else "connected",
                "issues": config_errors + ([f"Banco indisponível ({database_error})."] if not database_ok else []),
            },
        )
    return {"status": "ready", "database": "connected", "version": "18.2.0"}
