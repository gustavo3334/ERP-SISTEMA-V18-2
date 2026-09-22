from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import _classify_database
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_supabase_transaction_pooler_is_detected():
    provider, mode, host, port = _classify_database(
        "postgresql+psycopg://postgres.ref:secret@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
    )
    assert provider == "supabase"
    assert mode == "transaction"
    assert host.endswith("pooler.supabase.com")
    assert port == 6543


def test_supabase_session_pooler_is_supported():
    provider, mode, _, port = _classify_database(
        "postgresql+psycopg://postgres.ref:secret@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
    )
    assert provider == "supabase"
    assert mode == "session"
    assert port == 5432


def test_production_validation_accepts_supabase_postgres():
    settings = Settings(
        environment="production",
        auth_disabled=False,
        database_url="postgresql://postgres.ref:secret@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require",
        secret_key="x" * 64,
        seed_admin=False,
    )
    assert settings.runtime_validation_errors() == []


def test_serverless_startup_is_diagnostic_instead_of_hard_crash():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "settings.runtime_validation_errors()" in source
    assert "app.state.startup_issue" in source
    assert "settings.validate_runtime()" not in source


def test_transaction_pooler_disables_client_prepared_statements():
    source = (ROOT / "app" / "database.py").read_text(encoding="utf-8")
    assert 'connect_args["prepare_threshold"] = None' in source
    assert 'engine_kwargs["poolclass"] = NullPool' in source


def test_health_endpoint_remains_callable_and_reports_backend():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "online"
        assert data["version"] == "18.2.0"
        assert data["database"] in {"connected", "disconnected"}


def test_supabase_deploy_guide_and_env_example_exist():
    guide = (ROOT / "LEIA-ME-SUPABASE-VERCEL.txt").read_text(encoding="utf-8")
    env = (ROOT / ".env.production.example").read_text(encoding="utf-8")
    assert "Transaction Pooler" in guide
    assert "SEED_ADMIN=false" in env
    assert ":6543/postgres" in env


def test_main_has_controlled_database_and_configuration_errors():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '@app.exception_handler(SQLAlchemyError)' in source
    assert 'status_code=503' in source
    assert 'production_configuration_guard' in source
