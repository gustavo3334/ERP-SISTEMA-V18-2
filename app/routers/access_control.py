from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import delete,select
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_permission
from app.models import User
from app.models_extended import AccessProfile,AccessProfilePermission,UserAccessProfile
from app.schemas_extended import AccessProfileCreate,UserCreateExtended,UserUpdateExtended,UserPasswordReset
from app.security import hash_password

router=APIRouter(prefix="/access-control",tags=["Usuários e permissões"])
PERMISSIONS=["*","dashboard.read","clients.read","clients.write","products.read","products.write","inventory.read","inventory.write","purchasing.read","purchasing.write","purchasing.receive","sales.read","sales.write","sales.ship","pcp.read","pcp.write","deliveries.read","deliveries.write","finance.read","finance.write","rh.read","rh.write","rh.delete","rh.health.read","rh.health.write","rh.documents.read","rh.documents.write","rh.production.read","rh.production.write","rh.payroll","audit.read","settings.write"]

@router.get("/permissions",dependencies=[Depends(require_permission("settings.write"))])
def permissions():return PERMISSIONS

@router.get("/profiles",dependencies=[Depends(require_permission("settings.write"))])
def profiles(db:Session=Depends(get_db)):
    out=[]
    for p in db.scalars(select(AccessProfile).order_by(AccessProfile.name)).all():out.append({"id":p.id,"name":p.name,"description":p.description,"active":p.active,"permissions":list(db.scalars(select(AccessProfilePermission.permission).where(AccessProfilePermission.profile_id==p.id)).all())})
    return out

@router.post("/profiles",dependencies=[Depends(require_permission("settings.write"))])
def create_profile(payload:AccessProfileCreate,db:Session=Depends(get_db)):
    p=AccessProfile(name=payload.name,description=payload.description,active=payload.active);db.add(p);db.flush()
    for permission in sorted(set(payload.permissions)):db.add(AccessProfilePermission(profile_id=p.id,permission=permission))
    db.commit();return {"id":p.id,"name":p.name}

@router.put("/profiles/{profile_id}",dependencies=[Depends(require_permission("settings.write"))])
def update_profile(profile_id:str,payload:AccessProfileCreate,db:Session=Depends(get_db)):
    p=db.get(AccessProfile,profile_id)
    if not p:raise HTTPException(404,"Perfil não encontrado.")
    p.name=payload.name;p.description=payload.description;p.active=payload.active;db.execute(delete(AccessProfilePermission).where(AccessProfilePermission.profile_id==profile_id))
    for permission in sorted(set(payload.permissions)):db.add(AccessProfilePermission(profile_id=p.id,permission=permission))
    db.commit();return {"id":p.id,"name":p.name}

@router.get("/users",dependencies=[Depends(require_permission("settings.write"))])
def users(db:Session=Depends(get_db)):
    return [{"id":u.id,"email":u.email,"full_name":u.full_name,"role":u.role,"active":u.active,"profile_id":db.scalar(select(UserAccessProfile.profile_id).where(UserAccessProfile.user_id==u.id))} for u in db.scalars(select(User).order_by(User.email)).all()]

@router.post("/users",dependencies=[Depends(require_permission("settings.write"))])
def create_user(payload:UserCreateExtended,db:Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email==payload.email.lower())):raise HTTPException(409,"E-mail já cadastrado.")
    u=User(email=payload.email.lower(),full_name=payload.full_name,password_hash=hash_password(payload.password),role=payload.role,active=payload.active);db.add(u);db.flush()
    if payload.profile_id:db.add(UserAccessProfile(user_id=u.id,profile_id=payload.profile_id))
    db.commit();return {"id":u.id,"email":u.email}


@router.put("/users/{user_id}",dependencies=[Depends(require_permission("settings.write"))])
def update_user(user_id:str,payload:UserUpdateExtended,db:Session=Depends(get_db)):
    u=db.get(User,user_id)
    if not u:raise HTTPException(404,"Usuário não encontrado.")
    u.full_name=payload.full_name or u.full_name;u.role=payload.role;u.active=payload.active
    db.execute(delete(UserAccessProfile).where(UserAccessProfile.user_id==u.id))
    if payload.profile_id:db.add(UserAccessProfile(user_id=u.id,profile_id=payload.profile_id))
    db.commit();return {"id":u.id,"email":u.email,"full_name":u.full_name,"role":u.role,"active":u.active,"profile_id":payload.profile_id}

@router.post("/users/{user_id}/password",dependencies=[Depends(require_permission("settings.write"))])
def reset_user_password(user_id:str,payload:UserPasswordReset,db:Session=Depends(get_db)):
    u=db.get(User,user_id)
    if not u:raise HTTPException(404,"Usuário não encontrado.")
    u.password_hash=hash_password(payload.password);db.commit();return {"status":"ok","user_id":u.id}

@router.delete("/users/{user_id}",status_code=204,dependencies=[Depends(require_permission("settings.write"))])
def delete_user(user_id:str,db:Session=Depends(get_db)):
    u=db.get(User,user_id)
    if not u:raise HTTPException(404,"Usuário não encontrado.")
    if u.role=="administrator":
        admins=list(db.scalars(select(User).where(User.role=="administrator",User.active.is_(True))).all())
        if len(admins)<=1:raise HTTPException(409,"Não é possível excluir o último administrador ativo.")
    db.execute(delete(UserAccessProfile).where(UserAccessProfile.user_id==u.id));db.delete(u);db.commit();return None
