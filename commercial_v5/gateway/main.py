from __future__ import annotations

import base64
import hashlib
import io
import logging
import math
import threading
import secrets
from pathlib import Path
import json
import os
import re
import time
import uuid
from urllib.parse import urlsplit
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, JSON, LargeBinary, String, Text, create_engine, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
ERP_API_BASE = os.getenv("ERP_API_BASE", "http://127.0.0.1:8000/api/v1").rstrip("/")
ERP_INTERNAL_API_BASE = os.getenv("ERP_INTERNAL_API_BASE", "").strip().rstrip("/")
# Modo unificado: ERP e Comercial compartilham o mesmo processo/porta, evitando
# requisições externas entre serviços Free do Render. A URL é sempre loopback.
COMBINED_DEPLOYMENT = os.getenv("COMBINED_DEPLOYMENT", "").lower() == "true"
if COMBINED_DEPLOYMENT and ERP_INTERNAL_API_BASE:
    raise RuntimeError("Não configure ERP_INTERNAL_API_BASE no modo unificado")
try:
    COMBINED_PORT = int(os.getenv("PORT", "10000"))
except ValueError as exc:
    raise RuntimeError("PORT inválida para implantação unificada") from exc
if COMBINED_DEPLOYMENT and not 1 <= COMBINED_PORT <= 65535:
    raise RuntimeError("PORT fora do intervalo válido")



def _verified_erp_upstream(public_base: str, private_base: str, environment: str, on_render: bool) -> str:
    """Allow plaintext ERP traffic only to a tightly scoped Render private hostname.

    Render Free *receivers* don't accept private traffic: the destination ERP must
    be on a paid web plan. Never fall back to public transport on private failure.
    """
    if not private_base:
        return public_base
    parsed = urlsplit(private_base)
    # Render's service internal host is a single DNS label (e.g. erp-abc123),
    # not a URL controlled by browser input. Disallow public FQDNs and IPs.
    valid_host = bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,124}[a-z0-9])?", parsed.hostname or "")) and "-" in (parsed.hostname or "")
    try:
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("ERP_INTERNAL_API_BASE possui porta inválida") from exc
    if not (parsed.scheme == "http" and port == 10000 and valid_host
            and not parsed.username and not parsed.password and parsed.path == "/api/v1"
            and not parsed.query and not parsed.fragment):
        raise RuntimeError("ERP_INTERNAL_API_BASE deve ser http://HOST_INTERNO_RENDER:10000/api/v1")
    if environment == "production" and not on_render:
        raise RuntimeError("Conexão privada do ERP em produção exige ambiente Render")
    return private_base

CATALOG_DATABASE_URL = os.getenv("CATALOG_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///./facil_pedido_catalogo.db"))
ERP_SERVICE_EMAIL = os.getenv("ERP_SERVICE_EMAIL", "admin@facilpedido.local")
ERP_SERVICE_PASSWORD = os.getenv("ERP_SERVICE_PASSWORD", "TroqueEstaSenha123!")
REQUEST_TIMEOUT = float(os.getenv("ERP_REQUEST_TIMEOUT", "20"))
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
ERP_UPSTREAM_BASE = _verified_erp_upstream(
    ERP_API_BASE, ERP_INTERNAL_API_BASE, ENVIRONMENT,
    os.getenv("RENDER", "").strip().lower() == "true",
)
# O acesso interno é feito via 127.0.0.1, não por DNS público nem Render Private Network.
if COMBINED_DEPLOYMENT:
    ERP_UPSTREAM_BASE = f"http://127.0.0.1:{COMBINED_PORT}/api/v1"
ERP_CONNECTION_TYPE = "loopback" if COMBINED_DEPLOYMENT else ("private" if ERP_INTERNAL_API_BASE else "public")
MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(12 * 1024 * 1024)))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(6 * 1024 * 1024)))
MAX_PRODUCT_IMAGES = 12
# Sem armazenamento de senhas/tokens em logs ou cache persistente.
ERP_MAX_PARALLEL_CALLS = max(1, min(8, int(os.getenv("ERP_MAX_PARALLEL_CALLS", "2"))))
ERP_READ_RETRY_SECONDS = max(0.0, min(5.0, float(os.getenv("ERP_READ_RETRY_SECONDS", "3"))))
ERP_AUTH_CACHE_TTL = max(0.0, min(30.0, float(os.getenv("ERP_AUTH_CACHE_TTL", "12"))))
logger = logging.getLogger("facil_pedido_gateway")

if CATALOG_DATABASE_URL.startswith("postgres://"):
    CATALOG_DATABASE_URL = CATALOG_DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif CATALOG_DATABASE_URL.startswith("postgresql://"):
    CATALOG_DATABASE_URL = CATALOG_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if CATALOG_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(CATALOG_DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CatalogState(Base):
    __tablename__ = "commercial_catalog_state"
    key = Column(String(120), primary_key=True)
    payload = Column(JSON, nullable=False, default=dict)
    revision = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class ProductMedia(Base):
    __tablename__ = "commercial_product_media"
    id = Column(String(36), primary_key=True)
    product_id = Column(String(64), nullable=False, index=True)
    filename = Column(String(255), nullable=False, default="foto.jpg")
    content_type = Column(String(80), nullable=False, default="image/jpeg")
    content = Column(LargeBinary, nullable=False)
    created_by = Column(String(160), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class SalesOrder(Base):
    __tablename__ = "commercial_sales_orders"
    id = Column(String(36), primary_key=True)
    code = Column(String(80), unique=True, index=True, nullable=False)
    status = Column(String(80), nullable=False, default="Rascunho")
    payload = Column(JSON, nullable=False, default=dict)
    erp_quote_id = Column(String(64), nullable=True)
    integration_log = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# A criação automática de tabelas só é permitida no ambiente de desenvolvimento.
# Em produção execute as migrations versionadas antes de iniciar a aplicação.
# No modo unificado, AUTO_CREATE_TABLES pertence ao ERP principal.
# As tabelas comerciais sempre são migradas separadamente via Alembic.
if not COMBINED_DEPLOYMENT and os.getenv("AUTO_CREATE_TABLES", "true" if ENVIRONMENT != "production" else "false").lower() == "true":
    if ENVIRONMENT == "production":
        raise RuntimeError("AUTO_CREATE_TABLES não deve ser ativado em produção")
    Base.metadata.create_all(bind=engine)


def db_session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


# -----------------------------------------------------------------------------
# App / HTTP ERP
# -----------------------------------------------------------------------------
if ENVIRONMENT == "production":
    if ERP_SERVICE_EMAIL == "admin@facilpedido.local" or ERP_SERVICE_PASSWORD == "TroqueEstaSenha123!":
        raise RuntimeError("Configure a conta de integração no ambiente de produção")
    if not ERP_API_BASE.startswith("https://"):
        raise RuntimeError("ERP_API_BASE deve usar HTTPS em produção")
    if CORS_ORIGINS == ["*"] or any(not x.startswith("https://") for x in CORS_ORIGINS):
        raise RuntimeError("CORS_ORIGINS de produção deve listar apenas domínios HTTPS")
    if not CATALOG_DATABASE_URL.startswith("postgresql+psycopg://"):
        raise RuntimeError("CATALOG_DATABASE_URL em produção deve apontar para PostgreSQL persistente")
    if MAX_REQUEST_BYTES > 25 * 1024 * 1024:
        raise RuntimeError("Limite máximo de corpo muito alto")


app = FastAPI(
    title="Fácil Pedido Gateway ERP + Comercial",
    version="5.0.1",
    description="Camada de integração entre o ERP principal, Comercial, Gestão de Catálogo/RH e site público.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False if CORS_ORIGINS == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proteções HTTP aplicadas antes do processamento de JSON/imagens.
class RequestLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        length = headers.get(b"content-length")
        if length:
            try:
                if int(length) > self.max_bytes:
                    response = JSONResponse({"detail": "Requisição muito grande"}, status_code=413)
                    await response(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse({"detail": "Content-Length inválido"}, status_code=400)
                await response(scope, receive, send)
                return
        read_bytes = 0
        async def limited_receive():
            nonlocal read_bytes
            message = await receive()
            if message["type"] == "http.request":
                read_bytes += len(message.get("body", b""))
                if read_bytes > self.max_bytes:
                    raise HTTPException(status_code=413, detail="Requisição muito grande")
            return message
        await self.app(scope, limited_receive, send)

app.add_middleware(RequestLimitMiddleware, max_bytes=MAX_REQUEST_BYTES)

@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

client = httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=False)
_service_cache: dict[str, Any] = {"token": None, "expires": 0.0}
_service_lock = threading.Lock()
_user_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_user_cache_lock = threading.Lock()
_erp_slots = threading.BoundedSemaphore(ERP_MAX_PARALLEL_CALLS)
_upstream_limit_lock = threading.Lock()
_read_limited_until = 0.0


def _token_from_request(request: Request) -> str | None:
    value = request.headers.get("authorization", "")
    if value.lower().startswith("bearer "):
        return value.split(" ", 1)[1].strip()
    return None


def _retry_after_seconds(value: str | None) -> int:
    """Aceita tanto segundos quanto uma data HTTP; default conservador."""
    if value:
        try:
            return max(1, min(3600, int(math.ceil(float(value)))))
        except (ValueError, OverflowError):
            try:
                target = parsedate_to_datetime(value)
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                return max(1, min(3600, math.ceil((target - datetime.now(timezone.utc)).total_seconds())))
            except (TypeError, ValueError, OverflowError):
                pass
    return 30


def _erp_call(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: Any | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[int, Any, dict[str, str]]:
    """Controla rajadas contra o ERP e reenvia *somente leituras* uma vez no 429.

    Nunca repete login, pedidos, pagamentos ou outra escrita automaticamente.
    """
    global _read_limited_until
    method = method.upper()
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Reads are subject to a shared pause, but an inventory/query throttle must
    # never prevent a distinct user from *attempting* to authenticate.
    # The upstream remains responsible for its own login protections.
    if method == "GET":
        with _upstream_limit_lock:
            remaining = _read_limited_until - time.monotonic()
        if remaining > 0:
            wait = max(1, math.ceil(remaining))
            return (
                429,
                {"detail": f"Consultas temporariamente limitadas pelo ERP. Aguarde {wait} segundos."},
                {"Retry-After": str(wait), "X-FP-429-Origin": "read-cooldown"},
            )

    try:
        with _erp_slots:
            r = client.request(method, ERP_UPSTREAM_BASE + path, headers=headers, json=body, params=params)
    except httpx.RequestError as exc:
        logger.warning("ERP indisponível para %s %s: %s", method, path, type(exc).__name__)
        raise HTTPException(502, "ERP temporariamente indisponível") from exc

    if r.status_code == 429:
        # No Retry-After provided: three seconds was too optimistic and led to
        # repeated attempts. A conservative 30s default avoids hammering a
        # possibly rate-limited public service; it is not an exact reset time.
        explicit = bool(r.headers.get("retry-after"))
        delay = _retry_after_seconds(r.headers.get("retry-after"))
        if method == "GET":
            with _upstream_limit_lock:
                _read_limited_until = max(_read_limited_until, time.monotonic() + min(delay, 120))
        logger.warning(
            "ERP HTTP 429: method=%s path=%s transport=%s response_kind=%s retry_seconds=%s retry_header_present=%s",
            method, path, ERP_CONNECTION_TYPE,
            "json" if "application/json" in r.headers.get("content-type", "") else "non-json",
            delay, explicit,
        )
        return (
            429,
            {"detail": f"ERP limitou esta requisição. Aguarde pelo menos {delay} segundos; se persistir, verifique limites no Render."},
            {"Retry-After": str(delay), "X-FP-429-Origin": "erp-response"},
        )

    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            payload = r.json()
        except ValueError:
            payload = {"detail": "Resposta inválida do ERP"}
    else:
        payload = r.content
    return r.status_code, payload, {"content-type": ctype}



def _service_token(force: bool = False) -> str:
    with _service_lock:
        if not force and _service_cache.get("token") and float(_service_cache.get("expires", 0)) > time.time():
            return str(_service_cache["token"])
        status, data, meta = _erp_call(
            "POST", "/auth/login", body={"email": ERP_SERVICE_EMAIL, "password": ERP_SERVICE_PASSWORD},
        )
        if status == 429:
            raise HTTPException(429, "ERP limitou temporariamente a autenticação de integração", headers={"Retry-After": meta.get("Retry-After", "3")})
        if status >= 400 or not isinstance(data, dict) or not data.get("token"):
            raise HTTPException(502, "Não foi possível autenticar a integração no ERP. Confira a conta técnica.")
        _service_cache["token"] = data["token"]
        _service_cache["expires"] = time.time() + 60 * 25
        return str(data["token"])

def _erp_json(method: str, path: str, *, token: str | None = None, body: Any | None = None, params: dict[str, Any] | None = None, service_fallback: bool = False):
    status, data, meta = _erp_call(method, path, token=token, body=body, params=params)
    if status in (401, 403) and service_fallback:
        status, data, meta = _erp_call(method, path, token=_service_token(), body=body, params=params)
    if status >= 400:
        detail = data.get("detail") if isinstance(data, dict) else None
        raise HTTPException(status, detail or f"Erro do ERP ({status})", headers={"Retry-After": meta.get("Retry-After", "3")} if status == 429 else None)
    return data


def _normalize_role(role: str | None) -> str:
    role = (role or "").strip().lower()
    role = role.replace("ç", "c").replace("ã", "a").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return re.sub(r"[^a-z0-9]+", "_", role).strip("_")


def _extra_permissions(role: str | None) -> list[str]:
    r = _normalize_role(role)
    if r in {"administrator", "admin"}:
        return ["*"]
    if r in {"manager", "gerente"}:
        return [
            "catalog.read", "catalog.write", "catalog.publish", "clients.read", "clients.write",
            "sales.read", "sales.write", "inventory.read", "inventory.write", "production.read", "production.write",
            "delivery.read", "delivery.write", "finance.read", "finance.write", "reports.read", "settings.write", "users.write",
        ]
    if r in {"hr", "rh", "rh_catalogo", "hr_catalog"}:
        return ["catalog.read", "catalog.write", "catalog.publish"]
    if r in {"sales", "vendedor", "comercial"}:
        return ["catalog.read", "clients.read", "clients.write", "sales.read", "sales.write"]
    if r in {"stock", "estoque"}:
        return ["catalog.read", "inventory.read", "inventory.write"]
    if r in {"production", "producao"}:
        return ["catalog.read", "inventory.read", "production.read", "production.write"]
    if r in {"finance", "financeiro"}:
        return ["finance.read", "finance.write", "reports.read", "sales.read"]
    return ["catalog.read"]


def _current_user(request: Request) -> dict[str, Any]:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(401, "Não autenticado")
    # Reaproveita autenticação dentro da mesma requisição; nunca entre requisições de escrita.
    token_key = hashlib.sha256(token.encode("utf-8")).hexdigest()
    same_request = getattr(request.state, "erp_auth", None)
    if same_request and same_request[0] == token_key:
        return dict(same_request[1])
    read_only = request.method.upper() == "GET"
    if read_only and ERP_AUTH_CACHE_TTL:
        with _user_cache_lock:
            hit = _user_cache.get(token_key)
            if hit and hit[0] > time.monotonic():
                request.state.erp_auth = (token_key, hit[1])
                return dict(hit[1])
    user = _erp_json("GET", "/auth/me", token=token)
    if not isinstance(user, dict):
        raise HTTPException(401, "Usuário inválido")
    user = dict(user)
    user["permissions"] = _extra_permissions(user.get("role"))
    request.state.erp_auth = (token_key, user)
    if read_only and ERP_AUTH_CACHE_TTL:
        with _user_cache_lock:
            if len(_user_cache) >= 512:
                _user_cache.clear()
            _user_cache[token_key] = (time.monotonic() + ERP_AUTH_CACHE_TTL, user)
    return dict(user)


def _catalog_access(user: dict[str, Any]) -> dict[str, bool]:
    r = _normalize_role(user.get("role"))
    admin = r in {"administrator", "admin", "manager", "gerente"}
    hr = r in {"hr", "rh", "rh_catalogo", "hr_catalog"}
    sales = r in {"sales", "vendedor", "comercial"}
    return {
        "read": admin or hr or sales or r in {"stock", "estoque", "production", "producao", "viewer"},
        "write": admin or hr,
        "publish": admin or hr,
    }


def _require_catalog(request: Request, action: str) -> dict[str, Any]:
    user = _current_user(request)
    if not _catalog_access(user).get(action, False):
        raise HTTPException(403, "Sem permissão para esta operação de catálogo")
    return user


def _sanitized_product(p: dict[str, Any], *, hide_cost: bool) -> dict[str, Any]:
    if not hide_cost:
        return p
    hidden = {"cost", "technical_cost", "purchase_cost", "unit_cost", "average_cost"}
    return {k: v for k, v in p.items() if k not in hidden}


def _json_response(status: int, payload: Any, meta: dict[str, str] | None = None) -> Response:
    if status == 204:
        return Response(status_code=204)
    headers = {}
    if status == 429:
        headers = {
            "Retry-After": str((meta or {}).get("Retry-After", "30")),
            "X-FP-429-Origin": str((meta or {}).get("X-FP-429-Origin", "unknown")),
        }
    return Response(
        content=json.dumps(payload, ensure_ascii=False, default=str),
        status_code=status,
        media_type="application/json",
        headers=headers,
    )


@app.get("/api/v1/health/live")
def liveness():
    return {"status": "alive"}


@app.get("/api/v1/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(select(1))
        catalog_ok = True
    except Exception:
        catalog_ok = False
    try:
        status, data, _ = _erp_call("GET", "/health")
        erp_ok = status < 400
    except Exception as exc:
        erp_ok = False
        data = {"detail": str(exc)}
    return {
        "status": "ok" if erp_ok and catalog_ok else "partial",
        "version": "7.0.0",
        "gateway": "connected",
        "erp": "connected" if erp_ok else "unavailable",
        "erp_base": ERP_UPSTREAM_BASE if ENVIRONMENT != "production" else "configured",
        "erp_transport": ERP_CONNECTION_TYPE,
        "catalog_database": "connected" if catalog_ok else "unavailable",
        "erp_health": data,
    }


# -----------------------------------------------------------------------------
# Autenticação: usa exatamente o login do ERP principal
# -----------------------------------------------------------------------------
@app.post("/api/v1/auth/login")
async def auth_login(request: Request):
    body = await request.json()
    status, data, meta = await run_in_threadpool(_erp_call, "POST", "/auth/login", body=body)
    if status >= 400:
        return _json_response(status, data, meta)
    if isinstance(data, dict):
        user = data.get("user") or {}
        base = list(data.get("permissions") or [])
        extra = _extra_permissions(user.get("role"))
        if "*" in extra:
            data["permissions"] = ["*"]
        else:
            data["permissions"] = sorted(set(base + extra))
    return data


@app.get("/api/v1/auth/me")
def auth_me(request: Request):
    return _current_user(request)


# -----------------------------------------------------------------------------
# Proxy CRUD do ERP principal
# -----------------------------------------------------------------------------
ROLE_TO_ERP = {
    "rh_catalogo": "hr", "rh / catalogo": "hr", "rh / catálogo": "hr", "rh": "hr",
    "vendedor": "sales", "comercial": "sales", "gerente": "manager", "estoque": "stock",
    "producao": "production", "produção": "production", "financeiro": "finance",
}
PROXY_RESOURCES = ["products", "product-variants", "categories", "stock-locations", "clients", "quotes", "users"]


def _adapt_user_payload(resource: str, body: Any) -> Any:
    if resource != "users" or not isinstance(body, dict):
        return body
    out = dict(body)
    role = str(out.get("role") or "").strip().lower()
    if role:
        out["role"] = ROLE_TO_ERP.get(role, role)
    if "name" in out and "full_name" not in out:
        out["full_name"] = out.pop("name")
    return out


def _proxy_collection(resource: str, request: Request, method: str, body: Any | None = None):
    token = _token_from_request(request)
    if not token:
        raise HTTPException(401, "Não autenticado")
    params = dict(request.query_params)
    user = _current_user(request)
    if resource == "quotes" and method != "GET" and ENVIRONMENT == "production" and os.getenv("ENABLE_SALES_WRITES", "false").lower() != "true":
        raise HTTPException(503, "Orçamentos bloqueados até validar as políticas comerciais no ERP")
    if method != "GET" and resource in {"products", "product-variants", "categories", "stock-locations"} and _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente", "stock", "estoque"}:
        raise HTTPException(403, "Somente operações autorizadas podem alterar o cadastro técnico.")
    body = _adapt_user_payload(resource, body)
    status, data, meta = _erp_call(method, f"/{resource}", token=token, body=body, params=params)
    # RH/Catálogo pode não possuir products:read no ERP antigo. O gateway lê com conta de integração e mascara custos.
    if method == "GET" and resource in {"products", "product-variants", "categories", "stock-locations"} and status in (401, 403):
        user = _current_user(request)
        if _catalog_access(user)["read"]:
            status, data, meta = _erp_call(method, f"/{resource}", token=_service_token(), body=body, params=params)
    if resource in {"products", "product-variants"} and method == "GET" and status < 400 and isinstance(data, list):
        hide = _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente", "finance"}
        data = [_sanitized_product(dict(x), hide_cost=hide) for x in data]
    if resource == "users" and status < 400 and isinstance(data, list):
        for x in data:
            if isinstance(x, dict) and _normalize_role(x.get("role")) == "hr":
                x["display_role"] = "RH / Catálogo"
    return _json_response(status, data, meta)


def _proxy_item(resource: str, item_id: str, request: Request, method: str, body: Any | None = None):
    token = _token_from_request(request)
    if not token:
        raise HTTPException(401, "Não autenticado")
    user = _current_user(request)
    if resource == "quotes" and method != "GET" and ENVIRONMENT == "production" and os.getenv("ENABLE_SALES_WRITES", "false").lower() != "true":
        raise HTTPException(503, "Alterações comerciais bloqueadas até validar as políticas de preço")
    if method != "GET" and resource in {"products", "product-variants", "categories", "stock-locations"} and _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente", "stock", "estoque"}:
        raise HTTPException(403, "Somente operações autorizadas podem alterar o cadastro técnico.")
    body = _adapt_user_payload(resource, body)
    status, data, meta = _erp_call(method, f"/{resource}/{item_id}", token=token, body=body)
    if method == "GET" and resource in {"products", "product-variants", "categories", "stock-locations"} and status in (401, 403):
        user = _current_user(request)
        if _catalog_access(user)["read"]:
            status, data, meta = _erp_call(method, f"/{resource}/{item_id}", token=_service_token(), body=body)
    if resource in {"products", "product-variants"} and method == "GET" and status < 400 and isinstance(data, dict):
        hide = _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente", "finance"}
        data = _sanitized_product(data, hide_cost=hide)
    return _json_response(status, data, meta)


for _res in PROXY_RESOURCES:
    def make_collection(resource: str):
        async def endpoint(request: Request):
            body = None
            if request.method in {"POST", "PUT", "PATCH"}:
                try:
                    body = await request.json()
                except Exception:
                    body = None
            return _proxy_collection(resource, request, request.method, body)
        endpoint.__name__ = f"proxy_{resource.replace('-', '_')}_collection"
        return endpoint

    def make_item(resource: str):
        async def endpoint(item_id: str, request: Request):
            body = None
            if request.method in {"POST", "PUT", "PATCH"}:
                try:
                    body = await request.json()
                except Exception:
                    body = None
            return _proxy_item(resource, item_id, request, request.method, body)
        endpoint.__name__ = f"proxy_{resource.replace('-', '_')}_item"
        return endpoint

    app.add_api_route(f"/api/v1/{_res}", make_collection(_res), methods=["GET", "POST"])
    app.add_api_route(f"/api/v1/{_res}/{{item_id}}", make_item(_res), methods=["GET", "PUT", "DELETE"])


# -----------------------------------------------------------------------------
# Estoque compatível com o Comercial
# -----------------------------------------------------------------------------
@app.get("/api/v1/inventory/balances")
def inventory_balances(request: Request):
    user = _current_user(request)
    if not (_catalog_access(user)["read"] or _normalize_role(user.get("role")) in {"administrator", "manager", "finance", "stock"}):
        raise HTTPException(403, "Sem acesso ao estoque")
    token = _token_from_request(request)
    if not token:
        raise HTTPException(401, "Não autenticado")
    status, data, meta = _erp_call("GET", "/stock/balance", token=token, params={"limit": 1000})
    if status in (401, 403):
        status, data, meta = _erp_call("GET", "/stock/balance", token=_service_token(), params={"limit": 1000})
    if status in (404, 405, 501):
        # Compatibilidade com versões do ERP que ainda não expõem saldo por local.
        # Não coloque JSONResponse dentro do campo balances de outro endpoint:
        # o frontend espera SEMPRE uma lista e isso causa .filter is not a function.
        logger.warning("ERP sem endpoint compatível /stock/balance (%s): usando saldo geral do cadastro, sem detalhamento.", status)
        return []
    if status >= 400:
        detail = data.get("detail") if isinstance(data, dict) else None
        raise HTTPException(status, detail or f"Falha ao consultar saldos do ERP ({status})", headers={"Retry-After": meta.get("Retry-After", "3")} if status == 429 else None)
    if isinstance(data, dict):
        data = next((data[key] for key in ("items", "rows", "results", "data", "balances") if isinstance(data.get(key), list)), None)
    if not isinstance(data, list):
        raise HTTPException(502, "ERP retornou saldos em formato incompatível. Confira /stock/balance.")
    rows = []
    for x in data:
        if not isinstance(x, dict):
            raise HTTPException(502, "ERP retornou um item de saldo inválido.")
        rows.append({
            "id": f"{x.get('product_id')}:{x.get('location_id') or ''}",
            "product_id": x.get("product_id"),
            "variant_id": None,
            "location_id": x.get("location_id"),
            "quantity": float(x.get("stock") or 0),
            "reserved_quantity": float(x.get("reserved_stock") or 0),
            "available_quantity": float(x.get("available") or 0),
            "min_stock": float(x.get("min_stock") or 0),
        })
    return rows


@app.post("/api/v1/inventory/balances")
async def inventory_balance_save(request: Request):
    user = _current_user(request)
    if _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente", "stock", "estoque"}:
        raise HTTPException(403, "Sem permissão para movimentar estoque")
    token = _token_from_request(request)
    if not token:
        raise HTTPException(401, "Não autenticado")
    body = await request.json()
    payload = {
        "product_id": body.get("product_id"),
        "target_quantity": max(0, float(body.get("quantity") or 0)),
        "location_id": body.get("location_id"),
        "reason": body.get("reason") or "Ajuste pelo Fácil Pedido Comercial",
        "notes": body.get("notes") or "Sincronizado pelo gateway V5",
    }
    status, data, _ = _erp_call("POST", "/stock/adjust", token=token, body=payload)
    if status >= 400:
        return _json_response(status, data)
    return body


# -----------------------------------------------------------------------------
# Catálogo central + fotos RH
# -----------------------------------------------------------------------------
CATALOG_KEY = "facil-pedido-commercial-v7"


def _get_catalog_state(s: Session) -> dict[str, Any]:
    row = s.get(CatalogState, CATALOG_KEY)
    return {"payload": dict(row.payload or {}) if row else {}, "revision": int(row.revision or 0) if row else 0}


@app.get("/api/v1/catalog-management/access")
def catalog_access(request: Request):
    user = _current_user(request)
    a = _catalog_access(user)
    perms = _extra_permissions(user.get("role"))
    return {"permissions": perms, "can_read": a["read"], "can_write": a["write"], "can_publish": a["publish"]}


@app.post("/api/v1/catalog-management/bootstrap-profiles")
def catalog_profiles(request: Request):
    user = _current_user(request)
    if _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente"}:
        raise HTTPException(403, "Sem permissão")
    return {"profiles": ["Administrador", "Gerente", "Vendedor", "RH / Catálogo", "Estoque", "Produção", "Financeiro", "Logística"]}


@app.get("/api/v1/catalog-management/products")
def catalog_products(request: Request):
    user = _require_catalog(request, "read")
    token = _token_from_request(request)
    # Usa conta de integração se o ERP negar leitura de produto ao RH.
    def get(path: str):
        status, data, meta = _erp_call("GET", path, token=token, params={"limit": 500})
        if status in (401, 403):
            status, data, meta = _erp_call("GET", path, token=_service_token(), params={"limit": 500})
        if status >= 400:
            raise HTTPException(status, data.get("detail") if isinstance(data, dict) else "Erro no ERP", headers={"Retry-After": meta.get("Retry-After", "3")} if status == 429 else None)
        return data
    products = get("/products")
    hide = _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente", "finance"}
    products = [_sanitized_product(dict(p), hide_cost=hide) for p in products]
    balances = inventory_balances(request)
    # O catálogo continua navegável se o ERP não possuir saldos por local,
    # mas a UI deve indicar que o estoque detalhado não foi disponibilizado.
    return {
        "products": products,
        "variants": [_sanitized_product(dict(v), hide_cost=hide) for v in get("/product-variants")],
        "categories": get("/categories"),
        "locations": get("/stock-locations"),
        "balances": balances,
        "inventory_warning": ("Saldo detalhado não disponível: confira o estoque no ERP antes de negociar." if not balances and products else None),
    }


def _catalog_state_for_user(state: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    role = _normalize_role(user.get("role"))
    if role in {"administrator", "admin", "manager", "gerente"}:
        return state
    body = state.get("payload") or {}
    if role in {"hr", "rh", "rh_catalogo", "hr_catalog"}:
        safe = {k: body.get(k, {}) for k in ("media", "presentation")}
        safe["settings"] = {"companyName": (body.get("settings") or {}).get("companyName", "Fácil Pedido")}
    else:
        safe = {k: body.get(k, {}) for k in ("media", "presentation", "promotions", "crm", "quoteMeta", "settings")}
    return {"payload": safe, "revision": state.get("revision", 0)}


@app.get("/api/v1/catalog-management/state")
def catalog_state_get(request: Request, s: Session = Depends(db_session)):
    user = _require_catalog(request, "read")
    return _catalog_state_for_user(_get_catalog_state(s), user)


@app.put("/api/v1/catalog-management/state")
async def catalog_state_put(request: Request, s: Session = Depends(db_session)):
    user = _current_user(request)
    role = _normalize_role(user.get("role"))
    administrator = role in {"administrator", "admin", "manager", "gerente"}
    is_hr = role in {"hr", "rh", "rh_catalogo", "hr_catalog"}
    is_sales = role in {"sales", "vendedor", "comercial"}
    if not (administrator or is_hr or is_sales):
        raise HTTPException(403, "Sem permissão para salvar alterações comerciais")
    body = await request.json()
    proposed = body.get("payload")
    if not isinstance(proposed, dict):
        raise HTTPException(422, "Payload de catálogo inválido")
    row = s.scalar(select(CatalogState).where(CatalogState.key == CATALOG_KEY).with_for_update())
    revision = int(row.revision or 0) if row else 0
    base_revision = body.get("base_revision")
    if base_revision is None:
        raise HTTPException(428, "Informe base_revision para evitar sobrescrever alterações de outro usuário")
    if not isinstance(base_revision, int):
        raise HTTPException(422, "base_revision inválido")
    if base_revision != revision:
        raise HTTPException(409, "Catálogo atualizado por outro usuário. Atualize a página antes de salvar.")
    current = dict(row.payload or {}) if row else {}
    if administrator:
        payload = {**current, **proposed}
    else:
        allowed = {"media", "presentation"} if is_hr else {"crm", "quoteMeta"}
        payload = dict(current)
        for key in allowed:
            if key in proposed:
                if not isinstance(proposed[key], dict):
                    raise HTTPException(422, f"Campo {key} inválido")
                payload[key] = proposed[key]
        # Histórico é anexo somente para papéis limitados.
        if isinstance(proposed.get("history"), list):
            existing = list(current.get("history") or [])
            known = {str(x.get("id")) for x in existing if isinstance(x, dict)}
            new_entries = [x for x in proposed["history"] if isinstance(x, dict) and str(x.get("id")) not in known]
            for entry in new_entries[:15]:
                entry["user"] = user.get("full_name") or user.get("email")
                entry["at"] = utcnow().isoformat()
            payload["history"] = (new_entries[:15] + existing)[:500]
    for pid, entry in (payload.get("media") or {}).items():
        photos = entry.get("photos", []) if isinstance(entry, dict) else []
        if not isinstance(photos, list) or len(photos) > MAX_PRODUCT_IMAGES:
            raise HTTPException(422, "Máximo de 12 fotos por produto")
        if any(not isinstance(photo, str) or not (photo.startswith("https://") or photo.startswith("http://127.0.0.1:") or photo.startswith("http://localhost:")) for photo in photos):
            raise HTTPException(422, "Fotos devem ter URLs HTTP(S) válidas do armazenamento aprovado")
    for pid, entry in (payload.get("presentation") or {}).items():
        if isinstance(entry, dict) and entry.get("published") is True:
            media_entry = (payload.get("media") or {}).get(pid) or {}
            if not media_entry.get("photos"):
                raise HTTPException(422, "Não é permitido publicar produto sem foto")
    payload["lastEditedBy"] = user.get("full_name") or user.get("email") or "Usuário"
    payload["lastEditedAt"] = utcnow().isoformat()
    if not row:
        row = CatalogState(key=CATALOG_KEY, payload=payload, revision=1, updated_at=utcnow())
        s.add(row)
    else:
        row.payload = payload
        row.revision = revision + 1
        row.updated_at = utcnow()
    try:
        s.commit()
    except IntegrityError as exc:
        s.rollback()
        raise HTTPException(409, "Catálogo alterado por outro usuário. Atualize antes de salvar") from exc
    s.refresh(row)
    return _catalog_state_for_user({"payload": row.payload, "revision": row.revision}, user)


@app.post("/api/v1/catalog-management/products/{product_id}/publication")
async def set_publication(product_id: str, request: Request, s: Session = Depends(db_session)):
    user = _require_catalog(request, "publish")
    body = await request.json()
    published = bool(body.get("published"))
    erp_status, _, _ = _erp_call("GET", f"/products/{product_id}", token=_service_token())
    if erp_status >= 400:
        raise HTTPException(404, "Produto não encontrado no ERP")
    state = _get_catalog_state(s)
    if published:
        attached = ((state.get("payload") or {}).get("media") or {}).get(product_id) or {}
        if not attached.get("photos"):
            raise HTTPException(422, "Adicione uma imagem antes de publicar")
    payload = dict(state.get("payload") or {})
    presentation = dict(payload.get("presentation") or {})
    p = dict(presentation.get(product_id) or {})
    p["published"] = published
    presentation[product_id] = p
    payload["presentation"] = presentation
    row = s.get(CatalogState, CATALOG_KEY)
    if not row:
        row = CatalogState(key=CATALOG_KEY, payload=payload, revision=1, updated_at=utcnow()); s.add(row)
    else:
        row.payload = payload; row.revision += 1; row.updated_at = utcnow()
    s.commit(); s.refresh(row)
    return _catalog_state_for_user({"payload": row.payload, "revision": row.revision}, user)


class MediaInput(BaseModel):
    product_id: str
    filename: str = "foto.jpg"
    data_url: str


def _decode_data_url(value: str) -> tuple[str, bytes]:
    if len(value or "") > (MAX_IMAGE_BYTES * 4 // 3 + 200):
        raise HTTPException(413, "Imagem ultrapassa limite permitido")
    match = re.fullmatch(r"data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)", value or "")
    if not match:
        raise HTTPException(400, "Aceitamos imagens JPEG, PNG ou WebP em base64")
    try:
        raw = base64.b64decode(match.group(2), validate=True)
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Imagem maior que o limite permitido")
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(raw)) as image:
            if image.width < 1 or image.height < 1 or image.width * image.height > 24_000_000:
                raise HTTPException(413, "Resolução da imagem não permitida")
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise HTTPException(415, "Formato de imagem inválido")
            image.thumbnail((2200, 2200))
            out = io.BytesIO()
            image.convert("RGB").save(out, format="JPEG", quality=83, optimize=True)
            normalized = out.getvalue()
            if len(normalized) > MAX_IMAGE_BYTES:
                raise HTTPException(413, "Imagem convertida muito grande")
            return "image/jpeg", normalized
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise HTTPException(400, "Arquivo de imagem corrompido ou inválido") from exc


@app.post("/api/v1/media")
def media_upload(body: MediaInput, request: Request, s: Session = Depends(db_session)):
    user = _require_catalog(request, "write")
    ctype, raw = _decode_data_url(body.data_url)
    if not body.product_id or len(body.product_id) > 64:
        raise HTTPException(422, "Identificador de produto inválido")
    # Não aceita uploads vinculados a produtos inexistentes no ERP.
    product_status, _, _ = _erp_call("GET", f"/products/{body.product_id}", token=_service_token())
    if product_status >= 400:
        raise HTTPException(404, "Produto não encontrado no ERP")
    existing_count = s.scalar(select(func.count(ProductMedia.id)).where(ProductMedia.product_id == body.product_id)) or 0
    if existing_count >= MAX_PRODUCT_IMAGES:
        raise HTTPException(409, "Limite de 12 imagens por produto. Remova uma imagem antes de adicionar outra.")
    mid = str(uuid.uuid4())
    filename = Path(str(body.filename or "foto.jpg").replace("\\", "/")).name[:120]
    s.add(ProductMedia(
        id=mid, product_id=body.product_id, filename=filename,
        content_type=ctype, content=raw,
        created_by=user.get("full_name") or user.get("email") or user.get("id"),
        created_at=utcnow(),
    ))
    s.commit()
    return {"id": mid, "product_id": body.product_id, "path": f"/media/{mid}", "content_type": ctype}


@app.get("/api/v1/media/{media_id}")
def media_get(media_id: str, s: Session = Depends(db_session)):
    row = s.get(ProductMedia, media_id)
    if not row:
        raise HTTPException(404, "Imagem não encontrada")
    return Response(content=row.content, media_type=row.content_type, headers={"Cache-Control": "public, max-age=86400"})


@app.delete("/api/v1/media/{media_id}")
def media_delete(media_id: str, request: Request, s: Session = Depends(db_session)):
    _require_catalog(request, "write")
    row = s.get(ProductMedia, media_id)
    if not row:
        raise HTTPException(404, "Imagem não encontrada")
    s.delete(row); s.commit()
    return Response(status_code=204)


@app.get("/api/v1/client-management/front/state")
def client_front_state(request: Request):
    token = _token_from_request(request)
    data = _erp_json("GET", "/clients", token=token, params={"limit": 500})
    return {"clients": data}


@app.get("/api/v1/client-management/{client_id}/product-price/{product_id}")
def client_product_price(client_id: str, product_id: str, request: Request):
    user = _current_user(request)
    if not (_catalog_access(user)["read"] or _normalize_role(user.get("role")) in {"finance", "financeiro"}):
        raise HTTPException(403, "Sem permissão para consultar preços")
    token = _token_from_request(request)
    status, product, _ = _erp_call("GET", f"/products/{product_id}", token=token)
    if status in (401, 403):
        status, product, _ = _erp_call("GET", f"/products/{product_id}", token=_service_token())
    if status >= 400:
        return _json_response(status, product)
    return {"price": float(product.get("price") or 0)}


# -----------------------------------------------------------------------------
# Pedidos comerciais: persistem no MESMO banco do catálogo e sincronizam ERP
# -----------------------------------------------------------------------------
def _require_sales(request: Request) -> dict[str, Any]:
    user = _current_user(request)
    if _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente", "sales", "vendedor", "comercial"}:
        raise HTTPException(403, "Este perfil não pode acessar vendas")
    return user


def _order_dict(row: SalesOrder) -> dict[str, Any]:
    d = dict(row.payload or {})
    d.update({
        "id": row.id, "code": row.code, "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "erp_quote_id": row.erp_quote_id,
        "integration_log": list(row.integration_log or []),
    })
    return d


def _calc_order(payload: dict[str, Any]) -> dict[str, Any]:
    items = []
    subtotal = 0.0
    if not isinstance(payload.get("items"), list) or not 1 <= len(payload["items"]) <= 100:
        raise HTTPException(422, "O pedido deve conter de 1 a 100 itens")
    for i in payload.get("items") or []:
        q = float(i.get("quantity") or 0)
        unit = float(i.get("unit_price") or 0)
        disc = float(i.get("discount_percent") or i.get("discount") or 0)
        if not (0 < q <= 100_000 and 0 <= unit <= 10_000_000 and 0 <= disc <= 100):
            raise HTTPException(422, "Quantidade, valor ou desconto de item inválido")
        total = q * unit * (1 - max(0, min(100, disc)) / 100)
        item = {**i, "quantity": q, "unit_price": unit, "discount_percent": disc, "total": round(total, 2)}
        items.append(item); subtotal += total
    order_disc = float(payload.get("discount") or 0)
    freight = float(payload.get("freight") or 0)
    if not (0 <= order_disc <= 100 and 0 <= freight <= 1_000_000):
        raise HTTPException(422, "Desconto ou frete inválido")
    total = subtotal * (1 - max(0, min(100, order_disc)) / 100) + freight
    return {**payload, "items": items, "subtotal": round(subtotal, 2), "discount": order_disc, "freight": freight, "total": round(total, 2)}


def _next_order_code(s: Session) -> str:
    prefix = f"PED-{date.today().strftime('%Y%m%d')}-"
    # UUID evita colisões em pedidos simultâneos de diferentes vendedores.
    return prefix + uuid.uuid4().hex[:10].upper()


def _sync_order_as_quote(order: dict[str, Any], token: str) -> tuple[str | None, str]:
    body = {
        "client_id": order.get("client_id"),
        "client_name": order.get("client_name") or "",
        "valid_until": None,
        "probability": 100,
        "payment_method": order.get("payment_method") or "",
        "status": "Aprovado",
        "notes": f"Pedido comercial {order.get('code')} | {order.get('notes') or ''}".strip(),
        "items": [
            {
                "product_id": i.get("product_id"),
                "product_name": i.get("description") or i.get("product_name") or "Produto",
                "quantity": i.get("quantity") or 0,
                "unit_price": i.get("unit_price") or 0,
                "discount": i.get("discount_percent") or 0,
            }
            for i in order.get("items") or []
        ],
    }
    status, data, _ = _erp_call("POST", "/quotes", token=token, body=body)
    if status >= 400:
        return None, f"Orçamento espelho não criado no ERP: {data}"
    return str(data.get("id")) if isinstance(data, dict) else None, "Pedido espelhado no ERP como orçamento aprovado"


@app.get("/api/v1/sales-orders")
def orders_list(request: Request, s: Session = Depends(db_session)):
    _require_sales(request)
    rows = s.execute(select(SalesOrder).order_by(SalesOrder.created_at.desc())).scalars().all()
    return [_order_dict(x) for x in rows]


@app.post("/api/v1/sales-orders")
async def orders_create(request: Request, s: Session = Depends(db_session)):
    if ENVIRONMENT == "production" and os.getenv("ENABLE_SALES_WRITES", "false").lower() != "true":
        raise HTTPException(503, "Vendas bloqueadas em produção até validar preços, descontos e aprovação no ERP")
    user = _require_sales(request)
    r = _normalize_role(user.get("role"))
    if r not in {"administrator", "admin", "manager", "gerente", "sales", "vendedor", "comercial"}:
        raise HTTPException(403, "Sem permissão para criar pedido")
    payload = _calc_order(await request.json())
    oid = str(uuid.uuid4()); code = _next_order_code(s)
    payload["created_by"] = user.get("full_name") or user.get("email") or user.get("id")
    payload["code"] = code
    log: list[str] = []
    erp_quote_id = None
    # Espelha no ERP para o pedido aparecer na operação existente mesmo sem módulo SalesOrder legado.
    try:
        erp_quote_id, msg = _sync_order_as_quote({**payload, "code": code}, _token_from_request(request) or "")
        log.append(msg)
    except Exception as exc:
        log.append(f"Sincronização inicial pendente: {exc}")
    row = SalesOrder(id=oid, code=code, status="Rascunho", payload=payload, erp_quote_id=erp_quote_id, integration_log=log, created_at=utcnow(), updated_at=utcnow())
    s.add(row); s.commit(); s.refresh(row)
    return _order_dict(row)


@app.get("/api/v1/sales-orders/{order_id}")
def orders_get(order_id: str, request: Request, s: Session = Depends(db_session)):
    _require_sales(request)
    row = s.get(SalesOrder, order_id)
    if not row: raise HTTPException(404, "Pedido não encontrado")
    return _order_dict(row)


@app.put("/api/v1/sales-orders/{order_id}")
async def orders_update(order_id: str, request: Request, s: Session = Depends(db_session)):
    _require_sales(request)
    row = s.get(SalesOrder, order_id)
    if not row: raise HTTPException(404, "Pedido não encontrado")
    payload = _calc_order(await request.json())
    if row.status != "Rascunho":
        raise HTTPException(409, "Pedido já processado ou pendente de conciliação. Não é possível editar.")
    # Status não pode ser forjado pelo cliente; somente /confirm altera confirmação.
    payload.pop("status", None)
    row.payload = {**(row.payload or {}), **payload}; row.updated_at = utcnow()
    s.commit(); s.refresh(row)
    return _order_dict(row)


@app.delete("/api/v1/sales-orders/{order_id}")
def orders_delete(order_id: str, request: Request, s: Session = Depends(db_session)):
    user = _current_user(request)
    if _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente"}:
        raise HTTPException(403, "Somente gerente/administrador pode excluir pedido")
    row = s.get(SalesOrder, order_id)
    if not row: raise HTTPException(404, "Pedido não encontrado")
    if row.erp_quote_id or row.status != "Rascunho":
        raise HTTPException(409, "Pedido com vínculo no ERP não pode ser excluído sem conciliação")
    s.delete(row); s.commit(); return Response(status_code=204)


def _append_log(row: SalesOrder, message: str):
    arr = list(row.integration_log or []); arr.append(message); row.integration_log = arr


@app.post("/api/v1/sales-orders/{order_id}/confirm")
async def orders_confirm(order_id: str, request: Request, s: Session = Depends(db_session)):
    _require_sales(request)
    if ENVIRONMENT == "production" and os.getenv("ENABLE_AUTOMATED_ORDER_CONFIRMATION", "false").lower() != "true":
        raise HTTPException(503, "Confirmação automática bloqueada em produção até haver idempotência e conciliação garantidas no ERP")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    # Bloqueio de linha no PostgreSQL reduz confirmações concorrentes.
    row = s.scalar(select(SalesOrder).where(SalesOrder.id == order_id).with_for_update())
    if not row: raise HTTPException(404, "Pedido não encontrado")
    if row.status == "Confirmado":
        return {"order": _order_dict(row), "production_orders_created": []}
    if row.status == "Integração parcial" or (row.payload or {}).get("confirmed_at"):
        raise HTTPException(409, "Pedido já processado parcialmente. Concilie no ERP antes de tentar novamente; repetir pode duplicar efeitos financeiros e de estoque.")
    order = _order_dict(row)
    service = _service_token()
    productions = []
    # Saldo atual do ERP
    try:
        balances = _erp_json("GET", "/stock/balance", token=service, params={"limit": 1000})
    except Exception as exc:
        balances = []
        _append_log(row, f"Falha ao consultar estoque: {exc}")
    by_product = {str(x.get("product_id")): x for x in balances if isinstance(x, dict)}

    for item in order.get("items") or []:
        pid = str(item.get("product_id") or "")
        qty = float(item.get("quantity") or 0)
        bal = by_product.get(pid) or {}
        available = max(0.0, float(bal.get("available") or 0))
        reserve = min(qty, available)
        shortage = max(0.0, qty - reserve)
        if reserve > 0:
            status, data, _ = _erp_call("POST", "/stock/movements", token=service, body={
                "product_id": pid,
                "variant_id": item.get("variant_id"),
                "location_id": bal.get("location_id"),
                "movement_type": "RESERVA",
                "quantity": reserve,
                "unit_cost": 0,
                "reason": f"Reserva pedido {row.code}",
                "notes": "Gerada automaticamente pelo Fácil Pedido Comercial V5",
            })
            _append_log(row, "Estoque reservado" if status < 400 else f"Reserva de estoque falhou: {data}")
        if shortage > 0 and body.get("auto_create_production", True):
            status, data, _ = _erp_call("POST", "/production-orders", token=service, body={
                "order_ref": row.code,
                "product_id": pid or None,
                "production_mode": "PRODUZIR_DO_ZERO",
                "product_name": item.get("description") or item.get("product_name") or "Produto",
                "quantity": shortage,
                "forecast_date": (date.today() + timedelta(days=7)).isoformat(),
                "workflow_stage": "Novo pedido",
                "priority": "Normal",
                "notes": f"Gerada automaticamente pelo pedido {row.code}",
            })
            if status < 400:
                productions.append(data); _append_log(row, f"Produção criada para {shortage:g} unidade(s)")
            else:
                _append_log(row, f"Produção não criada: {data}")

    if body.get("create_receivable", True) and float(order.get("total") or 0) > 0:
        status, data, _ = _erp_call("POST", "/financial-entries", token=service, body={
            "kind": "Receita",
            "description": f"Pedido {row.code} - {order.get('client_name') or ''}",
            "category": "Vendas",
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "amount": float(order.get("total") or 0),
            "status": "A vencer",
            "notes": "Gerado automaticamente pelo Fácil Pedido Comercial V5",
        })
        _append_log(row, "Conta a receber criada" if status < 400 else f"Financeiro não sincronizado: {data}")

    if order.get("delivery_address"):
        status, data, _ = _erp_call("POST", "/deliveries", token=service, body={
            "client_id": order.get("client_id"),
            "order_ref": row.code,
            "recipient_name": order.get("client_name") or "Cliente",
            "address": order.get("delivery_address"),
            "scheduled_date": (date.today() + timedelta(days=3)).isoformat(),
            "route_name": "",
            "driver_name": "",
            "status": "Agendada",
            "occurrence": "",
            "notes": "Gerada automaticamente pelo Fácil Pedido Comercial V5",
        })
        _append_log(row, "Entrega agendada" if status < 400 else f"Entrega não criada: {data}")

    errors = [x for x in list(row.integration_log or []) if any(term in x.casefold() for term in ("falha", "não criada", "não criado", "não sincronizado", "pendente"))]
    row.status = "Confirmado" if not errors else "Integração parcial"
    row.updated_at = utcnow()
    payload = dict(row.payload or {}); payload["confirmed_at"] = utcnow().isoformat(); row.payload = payload
    s.commit(); s.refresh(row)
    return {"order": _order_dict(row), "production_orders_created": productions, "integration_warnings": errors}


# -----------------------------------------------------------------------------
# Integração / snapshot / catálogo público
# -----------------------------------------------------------------------------
@app.get("/api/v1/integration/snapshot")
def integration_snapshot(request: Request, s: Session = Depends(db_session)):
    user = _current_user(request)
    if _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente"}:
        raise HTTPException(403, "Snapshot administrativo indisponível para este perfil")
    service = _service_token()
    def get(path: str, **params):
        return _erp_json("GET", path, token=service, params=params or None)
    rows = s.execute(select(SalesOrder).order_by(SalesOrder.created_at.desc())).scalars().all()
    return {
        "products": get("/products", limit=500),
        "variants": get("/product-variants", limit=500),
        "categories": get("/categories", limit=500),
        "locations": get("/stock-locations", limit=500),
        "balances": get("/stock/balance", limit=1000),
        "clients": get("/clients", limit=500),
        "quotes": get("/quotes", limit=500),
        "orders": [_order_dict(x) for x in rows],
        "catalog": _get_catalog_state(s),
        "generated_at": utcnow().isoformat(),
        "source": "ERP principal + Gateway V5",
    }


class UpsertInput(BaseModel):
    kind: str
    data: dict[str, Any]


@app.post("/api/v1/integration/upsert")
def integration_upsert(body: UpsertInput, request: Request):
    user = _current_user(request)
    if _normalize_role(user.get("role")) not in {"administrator", "admin", "manager", "gerente"}:
        raise HTTPException(403, "Sem permissão para integração")
    mapping = {
        "product": "products", "variant": "product-variants", "category": "categories",
        "location": "stock-locations", "client": "clients", "quote": "quotes",
    }
    resource = mapping.get(body.kind)
    if not resource:
        raise HTTPException(400, "Tipo de integração não suportado")
    item_id = body.data.get("id")
    token = _service_token()
    if item_id:
        status, data, _ = _erp_call("PUT", f"/{resource}/{item_id}", token=token, body=body.data)
        if status == 404:
            status, data, _ = _erp_call("POST", f"/{resource}", token=token, body=body.data)
    else:
        status, data, _ = _erp_call("POST", f"/{resource}", token=token, body=body.data)
    return _json_response(status, data)


def _public_products(s: Session) -> list[dict[str, Any]]:
    state = _get_catalog_state(s).get("payload") or {}
    presentation = state.get("presentation") or {}
    media = state.get("media") or {}
    try:
        products = _erp_json("GET", "/products", token=_service_token(), params={"limit": 500})
    except Exception as exc:
        logger.warning("Catálogo público: falha ao consultar ERP: %s", type(exc).__name__)
        raise HTTPException(503, "Catálogo temporariamente indisponível. Tente novamente.") from exc
    out = []
    for p in products if isinstance(products, list) else []:
        pid = str(p.get("id") or "")
        pres = presentation.get(pid) or {}
        if pres.get("published") is not True or p.get("active") is False:
            continue
        photos = list((media.get(pid) or {}).get("photos") or [])
        out.append({
            "id": pid,
            "code": p.get("code"),
            "name": pres.get("title") or p.get("name"),
            "description": pres.get("description") or p.get("description") or "",
            "subtitle": pres.get("subtitle") or "",
            "price": float(p.get("price") or 0),
            "category_id": p.get("category_id"),
            "color": p.get("color"),
            "size": p.get("size"),
            "photos": photos,
            "cover": photos[0] if photos else None,
        })
    return out


@app.get("/api/v1/public/catalog")
def public_catalog(s: Session = Depends(db_session)):
    return {"products": _public_products(s), "updated_at": utcnow().isoformat()}


@app.get("/api/v1/public/catalog/{product_id}")
def public_product(product_id: str, s: Session = Depends(db_session)):
    for p in _public_products(s):
        if p["id"] == product_id:
            return p
    raise HTTPException(404, "Produto não publicado")


WEB_ROOT = Path(__file__).resolve().parent.parent


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(WEB_ROOT / "comercial" / "index.html", media_type="text/html")


@app.get("/site-demo.html", include_in_schema=False)
def site_preview():
    return FileResponse(WEB_ROOT / "site-demo.html", media_type="text/html")
