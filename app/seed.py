from __future__ import annotations

from sqlalchemy import select

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import User
from app.models_extended import AccessProfile, AccessProfilePermission
from app.security import hash_password


def main() -> None:
    from app import models_extended  # noqa: F401
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        default_profiles = {
            "Administrador": ["*"],
            "Gerente": ["dashboard.read","clients.read","clients.write","products.read","products.write","inventory.read","inventory.write","purchasing.read","purchasing.write","purchasing.receive","sales.read","sales.write","sales.ship","pcp.read","pcp.write","deliveries.read","deliveries.write","finance.read","finance.write","rh.read","audit.read"],
            "Vendedor": ["dashboard.read","clients.read","clients.write","products.read","sales.read","sales.write","deliveries.read"],
            "Financeiro": ["dashboard.read","clients.read","sales.read","purchasing.read","finance.read","finance.write"],
            "Produção": ["dashboard.read","products.read","inventory.read","pcp.read","pcp.write"],
            "Estoque": ["dashboard.read","products.read","inventory.read","inventory.write","purchasing.read","purchasing.receive"],
            "Recursos Humanos": ["dashboard.read","rh.read","rh.write","rh.documents.read","rh.documents.write","rh.production.read","rh.production.write","rh.payroll"],
            "Compras": ["dashboard.read","products.read","inventory.read","purchasing.read","purchasing.write","purchasing.receive","finance.read"],
        }
        for profile_name, permissions in default_profiles.items():
            profile = db.scalar(select(AccessProfile).where(AccessProfile.name == profile_name))
            if profile is None:
                profile = AccessProfile(name=profile_name, description=f"Perfil padrão: {profile_name}.", active=True)
                db.add(profile); db.flush()
                for permission in permissions:
                    db.add(AccessProfilePermission(profile_id=profile.id, permission=permission))
        db.commit()

    if not settings.seed_admin:
        print("Banco preparado sem dados demonstrativos.")
        print("AUTH_DISABLED está configurado para acesso temporário sem login.")
        return

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == settings.admin_email.lower()))
        if user is None:
            user = User(
                email=settings.admin_email.lower(),
                full_name=settings.admin_name,
                password_hash=hash_password(settings.admin_password),
                role="administrator",
                active=True,
            )
            db.add(user)
            db.commit()
            print(f"Administrador criado: {settings.admin_email}")
        else:
            print("Administrador já existe.")


if __name__ == "__main__":
    main()
