from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import SessionLocal
from app.models import User, StockLocation
from app.models_extended import AccessProfile, AccessProfilePermission
from app.security import hash_password


DEFAULT_STOCK_LOCATIONS: list[dict[str, str]] = [
    {
        "name": "Estoque Principal",
        "warehouse": "Principal",
        "address_code": "EST-PRINCIPAL",
        "description": "Local padrão para produtos acabados e saldo geral.",
    },
    {
        "name": "Matéria-prima",
        "warehouse": "Principal",
        "address_code": "MAT-PRIMA",
        "description": "Local padrão para matérias-primas e insumos.",
    },
    {
        "name": "Expedição",
        "warehouse": "Principal",
        "address_code": "EXPEDICAO",
        "description": "Produtos separados e aguardando saída/entrega.",
    },
    {
        "name": "Quarentena / Avarias",
        "warehouse": "Principal",
        "address_code": "QUARENTENA",
        "description": "Itens bloqueados, avariados ou aguardando conferência.",
    },
]


DEFAULT_PROFILES: dict[str, list[str]] = {
    "Administrador": ["*"],
    "Gerente": [
        "dashboard.read", "clients.read", "clients.write", "products.read", "products.write",
        "inventory.read", "inventory.write", "purchasing.read", "purchasing.write",
        "purchasing.receive", "sales.read", "sales.write", "sales.ship", "pcp.read",
        "pcp.write", "deliveries.read", "deliveries.write", "finance.read", "finance.write",
        "rh.read", "audit.read",
    ],
    "Vendedor": ["dashboard.read", "clients.read", "clients.write", "products.read", "sales.read", "sales.write", "deliveries.read"],
    "Financeiro": ["dashboard.read", "clients.read", "sales.read", "purchasing.read", "finance.read", "finance.write"],
    "Produção": ["dashboard.read", "products.read", "inventory.read", "pcp.read", "pcp.write"],
    "Estoque": ["dashboard.read", "products.read", "inventory.read", "inventory.write", "purchasing.read", "purchasing.receive"],
    "Recursos Humanos": ["dashboard.read", "rh.read", "rh.write", "rh.documents.read", "rh.documents.write", "rh.production.read", "rh.production.write", "rh.payroll"],
    "Compras": ["dashboard.read", "products.read", "inventory.read", "purchasing.read", "purchasing.write", "purchasing.receive", "finance.read"],
}


def _seed_stock_locations() -> None:
    """Garante os locais operacionais mínimos sem apagar cadastros do cliente.

    Versões anteriores só criavam os padrões quando a tabela estava 100% vazia.
    Isso deixava instalações antigas sem opções válidas quando existia um registro
    incompleto ou legado. Agora cada código padrão é verificado individualmente.
    """
    with SessionLocal() as db:
        try:
            existing_codes = {
                str(code or "").strip().upper()
                for code in db.scalars(select(StockLocation.address_code)).all()
            }
            created = False
            for item in DEFAULT_STOCK_LOCATIONS:
                code = item["address_code"].strip().upper()
                if code in existing_codes:
                    continue
                db.add(
                    StockLocation(
                        name=item["name"],
                        warehouse=item["warehouse"],
                        aisle="",
                        rack="",
                        shelf="",
                        address_code=item["address_code"],
                        description=item["description"],
                        active=True,
                    )
                )
                existing_codes.add(code)
                created = True
            if created:
                db.commit()
        except IntegrityError:
            # Idempotência para cold starts concorrentes (ex.: Vercel).
            db.rollback()


def bootstrap_operational_defaults() -> None:
    _seed_stock_locations()


def _seed_profiles() -> None:
    with SessionLocal() as db:
        try:
            for profile_name, permissions in DEFAULT_PROFILES.items():
                profile = db.scalar(select(AccessProfile).where(AccessProfile.name == profile_name))
                if profile is None:
                    profile = AccessProfile(
                        name=profile_name,
                        description=f"Perfil padrão: {profile_name}.",
                        active=True,
                    )
                    db.add(profile)
                    db.flush()
                existing = set(
                    db.scalars(
                        select(AccessProfilePermission.permission).where(
                            AccessProfilePermission.profile_id == profile.id
                        )
                    ).all()
                )
                for permission in permissions:
                    if permission not in existing:
                        db.add(AccessProfilePermission(profile_id=profile.id, permission=permission))
            db.commit()
        except IntegrityError:
            # Outra instância serverless pode ter concluído o mesmo bootstrap em paralelo.
            db.rollback()


def _seed_admin() -> None:
    if not settings.seed_admin:
        return
    email = settings.admin_email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)) is not None:
            return
        db.add(
            User(
                email=email,
                full_name=settings.admin_name.strip() or "Administrador",
                password_hash=hash_password(settings.admin_password),
                role="administrator",
                active=True,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            # Idempotência para cold starts concorrentes.
            db.rollback()


def bootstrap_database() -> None:
    _seed_profiles()
    _seed_admin()
