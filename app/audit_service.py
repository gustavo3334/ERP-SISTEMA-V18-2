from __future__ import annotations
from typing import Any
from sqlalchemy.orm import Session
from app.models_extended import AuditLog


def audit(db: Session, *, module: str, action: str, entity_type: str = "", entity_id: str = "", description: str = "", user_id: str | None = None, user_name: str = "", before: dict[str, Any] | None = None, after: dict[str, Any] | None = None, ip_address: str = "") -> AuditLog:
    record = AuditLog(module=module, action=action, entity_type=entity_type, entity_id=entity_id, description=description, user_id=user_id, user_name=user_name, before_data=before or {}, after_data=after or {}, ip_address=ip_address)
    db.add(record)
    return record
