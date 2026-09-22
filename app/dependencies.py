from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import CurrentUser
from app.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if settings.auth_disabled:
        return CurrentUser(
            id="system",
            email="",
            full_name="",
            role="administrator",
            active=True,
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não informado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = str(payload.get("sub") or "")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )

    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        active=user.active,
    )


def require_permission(permission: str):
    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> CurrentUser:
        if settings.auth_disabled or current_user.role == "administrator":
            return current_user
        from sqlalchemy import select
        from app.models_extended import UserAccessProfile, AccessProfilePermission
        profile_id = db.scalar(select(UserAccessProfile.profile_id).where(UserAccessProfile.user_id == current_user.id))
        if not profile_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário sem perfil de acesso.")
        allowed = db.scalar(select(AccessProfilePermission.permission).where(AccessProfilePermission.profile_id == profile_id, AccessProfilePermission.permission.in_([permission, "*"])))
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permissão necessária: {permission}")
        return current_user
    return dependency
