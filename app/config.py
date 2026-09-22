from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fácil Pedido ERP"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/facil_pedido.db"
    database_connect_timeout_seconds: int = 10

    auth_disabled: bool = True
    secret_key: str = "troque-esta-chave"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480

    seed_admin: bool = False
    admin_email: str = "admin@facilpedido.local"
    admin_password: str = "TroqueEstaSenha123!"
    admin_name: str = "Administrador"

    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    auto_create_tables: bool = True
    frontend_dir: str = "frontend"

    # Backend completo / arquivos / backups
    upload_dir: str = "storage/uploads"
    backup_dir: str = "backup"
    max_upload_mb: int = 15
    allowed_upload_extensions: str = ".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv"
    company_address: str = "Rodovia João Afonso de Souza Castellano, 1800"
    registration_alert_warning_days: int = 3
    registration_alert_danger_days: int = 5

    # Rotas / geocodificação
    route_provider: str = "auto"  # auto, google ou osm
    google_maps_api_key: str = ""
    route_country_code: str = "br"
    route_timeout_seconds: int = 25
    route_user_agent: str = "FacilPedidoERP/16.0"
    route_contact_email: str = ""
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    osrm_base_url: str = "https://router.project-osrm.org"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def frontend_path(self) -> Path:
        return Path(self.frontend_dir).resolve()

    @property
    def is_vercel(self) -> bool:
        return str(os.getenv("VERCEL", "")).strip().lower() in {"1", "true", "yes"}

    @property
    def requires_production_security(self) -> bool:
        return self.is_vercel or self.environment.lower() in {"production", "prod"}

    def runtime_validation_errors(self) -> list[str]:
        """Retorna erros de configuração sem derrubar o processo serverless."""
        if not self.requires_production_security:
            return []
        errors: list[str] = []
        if self.auth_disabled:
            errors.append("AUTH_DISABLED precisa ser false em produção.")
        raw_database_url = self.database_url.strip().lower()
        if raw_database_url.startswith("sqlite"):
            errors.append("DATABASE_URL precisa apontar para PostgreSQL persistente (Supabase).")
        elif not raw_database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            errors.append("DATABASE_URL precisa ser uma URL PostgreSQL válida.")
        secret = self.secret_key.strip()
        if len(secret) < 32 or secret in {"troque-esta-chave", "GERE_UMA_CHAVE_LONGA_E_ALEATORIA"}:
            errors.append("SECRET_KEY precisa ter pelo menos 32 caracteres aleatórios.")
        if self.seed_admin:
            if "@" not in self.admin_email:
                errors.append("ADMIN_EMAIL inválido para o bootstrap do administrador.")
            if len(self.admin_password) < 12 or self.admin_password == "TroqueEstaSenha123!":
                errors.append("ADMIN_PASSWORD precisa ter pelo menos 12 caracteres e não pode ser a senha padrão.")
        return errors

    def validate_runtime(self) -> None:
        errors = self.runtime_validation_errors()
        if errors:
            raise RuntimeError("Configuração de produção inválida: " + " ".join(errors))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
