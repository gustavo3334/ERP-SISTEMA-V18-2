from __future__ import annotations
from datetime import datetime
from pathlib import Path
import shutil
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.dependencies import require_permission
from app.models_extended import AuditLog,SystemSetting
from app.schemas_extended import SettingPayload

router=APIRouter(prefix="/system",tags=["Sistema / Auditoria"])

@router.get("/audit",dependencies=[Depends(require_permission("audit.read"))])
def logs(module:str|None=None,limit:int=200,db:Session=Depends(get_db)):
    s=select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit,1000))
    if module:s=s.where(AuditLog.module==module)
    return [{"id":x.id,"created_at":x.created_at,"user_id":x.user_id,"user_name":x.user_name,"module":x.module,"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"description":x.description,"before":x.before_data,"after":x.after_data} for x in db.scalars(s).all()]

@router.get("/settings/{key}")
def get_setting(key:str,db:Session=Depends(get_db)):
    x=db.scalar(select(SystemSetting).where(SystemSetting.setting_key==key));return {"key":key,"payload":x.payload if x else {}}

@router.put("/settings/{key}",dependencies=[Depends(require_permission("settings.write"))])
def set_setting(key:str,payload:SettingPayload,db:Session=Depends(get_db)):
    x=db.scalar(select(SystemSetting).where(SystemSetting.setting_key==key))
    if x is None:x=SystemSetting(setting_key=key,payload=payload.payload);db.add(x)
    else:x.payload=payload.payload
    db.commit();return {"key":key,"payload":x.payload}

@router.post("/backup",dependencies=[Depends(require_permission("settings.write"))])
def backup():
    if not settings.database_url.startswith("sqlite:///"):raise HTTPException(409,"Para PostgreSQL use backup gerenciado ou pg_dump.")
    source=Path(settings.database_url.replace("sqlite:///","",1)).resolve()
    if not source.exists():raise HTTPException(404,"Banco SQLite não encontrado.")
    target_dir=Path(settings.backup_dir).resolve();target_dir.mkdir(parents=True,exist_ok=True);target=target_dir/f"facil_pedido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db";shutil.copy2(source,target);return {"status":"ok","backup":str(target)}


@router.get("/environment")
def environment_info():
    """Informações públicas mínimas para o front identificar o ambiente."""
    return {
        "environment": settings.environment,
        "app_name": settings.app_name,
        "homologation": settings.environment.lower() in {"homologation", "homologacao", "staging"},
        "auth_disabled": settings.auth_disabled,
        "database": "sqlite" if settings.database_url.startswith("sqlite") else "postgresql",
    }
