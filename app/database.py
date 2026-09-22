from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    pass


@dataclass(frozen=True)
class DatabaseRuntime:
    provider: str
    pool_mode: str
    host: str
    port: int | None
    engine_error: str | None = None


def _normalized_database_url(raw: str) -> str:
    value = str(raw or "").strip()
    # SQLAlchemy tenta psycopg2 quando recebe apenas postgresql://. O projeto usa
    # psycopg 3, então normalizamos o driver de modo transparente.
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


def _classify_database(url: str) -> tuple[str, str, str, int | None]:
    try:
        parsed = make_url(url)
        host = str(parsed.host or "")
        port = parsed.port
        if parsed.drivername.startswith("sqlite"):
            return "sqlite", "local", host, port
        if "supabase" in host.lower():
            # O Transaction Pooler do Supabase usa porta 6543. O Session Pooler
            # usa 5432. Ambos são suportados por esta configuração.
            mode = "transaction" if port == 6543 else "session"
            return "supabase", mode, host, port
        if "neon.tech" in host.lower():
            return "neon", "pooled" if "pooler" in host.lower() else "direct", host, port
        if parsed.drivername.startswith("postgresql"):
            return "postgresql", "standard", host, port
        return parsed.drivername or "unknown", "standard", host, port
    except Exception:
        return "unknown", "unknown", "", None


database_url = _normalized_database_url(settings.database_url)
provider, pool_mode, database_host, database_port = _classify_database(database_url)
engine: Engine | None = None
engine_init_error: str | None = None

try:
    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif database_url.startswith("postgresql+psycopg"):
        connect_args["connect_timeout"] = max(3, int(settings.database_connect_timeout_seconds))

        # Supabase Transaction Pooler (PgBouncer / porta 6543) não deve receber
        # prepared statements do cliente. Psycopg 3 permite desabilitá-los com
        # prepare_threshold=None. Em serverless usamos NullPool para não manter
        # conexões locais ociosas entre invocações.
        if provider == "supabase" and pool_mode == "transaction":
            connect_args["prepare_threshold"] = None
            engine_kwargs["poolclass"] = NullPool
        elif settings.is_vercel:
            # Para Session Pooler/Neon/outro PostgreSQL na Vercel, deixamos o
            # pool remoto fazer o gerenciamento e não retemos conexões locais.
            engine_kwargs["poolclass"] = NullPool

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )
except Exception as exc:  # Mantém a aplicação inicializável para diagnóstico.
    engine_init_error = type(exc).__name__
    engine = None


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def database_runtime() -> DatabaseRuntime:
    return DatabaseRuntime(
        provider=provider,
        pool_mode=pool_mode,
        host=database_host,
        port=database_port,
        engine_error=engine_init_error,
    )


def check_database_connection() -> tuple[bool, str | None]:
    if engine is None:
        return False, engine_init_error or "engine_unavailable"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        # Não devolvemos a mensagem completa porque ela pode conter host,
        # usuário ou outros detalhes sensíveis da connection string.
        return False, type(exc).__name__


def get_db() -> Generator[Session, None, None]:
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados não inicializado. Confira DATABASE_URL.",
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
