from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import CurrentUser, LoginRequest, LoginResponse
from app.security import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    if settings.auth_disabled:
        user = CurrentUser(
            id="system",
            email="",
            full_name="",
            role="administrator",
            active=True,
        )
        return LoginResponse(
            token=create_access_token("system", {"role": "administrator"}),
            user=user,
            permissions=["*"],
        )

    identifier = str(payload.email or payload.username or "").strip().lower()
    user = db.scalar(
        select(User).where(
            or_(
                User.email.ilike(identifier),
                User.id == identifier,
            )
        )
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
        )
    if not user.active:
        raise HTTPException(status_code=403, detail="Usuário inativo.")

    current = CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        active=user.active,
    )
    return LoginResponse(
        token=create_access_token(user.id, {"role": user.role}),
        user=current,
        permissions=["*"] if user.role == "administrator" else [],
    )


@router.get("/me", response_model=CurrentUser)
def me(current_user: CurrentUser = Depends(get_current_user)):
    return current_user
