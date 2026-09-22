from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_fastapi_entrypoint_exists_and_exports_app():
    source = (ROOT / "index.py").read_text(encoding="utf-8")
    assert "from app.main import app" in source


def test_public_build_requires_auth_and_has_only_runtime_assets():
    public = ROOT / "public"
    config = (public / "config.js").read_text(encoding="utf-8")
    assert "window.FP_AUTH_REQUIRED = true" in config
    assert not (public / "vercel.json").exists()
    assert [p.name for p in public.glob("*.txt") if p.name != "robots.txt"] == []
    assert not list(public.glob("*.md"))


def test_production_guardrails_reject_insecure_settings():
    settings = Settings(
        environment="production",
        auth_disabled=True,
        database_url="sqlite:///./data/facil_pedido.db",
        secret_key="fraca",
    )
    with pytest.raises(RuntimeError) as exc:
        settings.validate_runtime()
    message = str(exc.value)
    assert "AUTH_DISABLED" in message
    assert "PostgreSQL" in message
    assert "SECRET_KEY" in message


def test_production_guardrails_accept_secure_postgres_settings():
    settings = Settings(
        environment="production",
        auth_disabled=False,
        database_url="postgresql://user:pass@host/db?sslmode=require",
        secret_key="x" * 64,
        seed_admin=True,
        admin_email="admin@example.com",
        admin_password="SenhaMuitoForte123!",
    )
    settings.validate_runtime()


def test_runtime_requirements_do_not_ship_test_dependencies():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
    assert "pytest" not in runtime
    assert "httpx" not in runtime
    assert "pytest" in dev
    assert "httpx" in dev
