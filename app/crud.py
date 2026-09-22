from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import String, cast, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.dependencies import get_current_user, require_permission


ModelT = TypeVar("ModelT", bound=Base)


def build_crud_router(
    *,
    model: type[ModelT],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    read_schema: type[BaseModel],
    prefix: str,
    tag: str,
    search_fields: Sequence[str] = (),
    read_permission: str | None = None,
    write_permission: str | None = None,
    delete_permission: str | None = None,
) -> APIRouter:
    router = APIRouter(
        prefix=f"/{prefix}",
        tags=[tag],
        dependencies=[Depends(get_current_user)],
    )

    read_dependencies = [Depends(require_permission(read_permission))] if read_permission else []
    write_dependencies = [Depends(require_permission(write_permission))] if write_permission else []
    delete_dependencies = [Depends(require_permission(delete_permission or write_permission))] if (delete_permission or write_permission) else []

    @router.get("", response_model=list[read_schema], dependencies=read_dependencies)
    def list_records(
        q: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        db: Session = Depends(get_db),
    ):
        statement = select(model)
        if q and search_fields:
            filters = [
                cast(getattr(model, field), String).ilike(f"%{q}%")
                for field in search_fields
            ]
            statement = statement.where(or_(*filters))
        statement = statement.order_by(model.created_at.desc()).offset(offset).limit(limit)
        return list(db.scalars(statement).all())

    @router.get("/{record_id}", response_model=read_schema, dependencies=read_dependencies)
    def get_record(record_id: str, db: Session = Depends(get_db)):
        record = db.get(model, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")
        return record

    @router.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED, dependencies=write_dependencies)
    def create_record(
        payload: dict[str, Any] = Body(...),
        db: Session = Depends(get_db),
    ):
        parsed = create_schema.model_validate(payload)
        record = model(**parsed.model_dump())
        db.add(record)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Já existe um registro com um código ou identificador igual.",
            ) from exc
        db.refresh(record)
        return record

    @router.put("/{record_id}", response_model=read_schema, dependencies=write_dependencies)
    def update_record(
        record_id: str,
        payload: dict[str, Any] = Body(...),
        db: Session = Depends(get_db),
    ):
        record = db.get(model, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")
        parsed = update_schema.model_validate(payload)
        for key, value in parsed.model_dump(exclude_unset=True).items():
            setattr(record, key, value)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Não foi possível salvar porque existe um identificador duplicado.",
            ) from exc
        db.refresh(record)
        return record

    @router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=delete_dependencies)
    def delete_record(record_id: str, db: Session = Depends(get_db)):
        record = db.get(model, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")
        db.delete(record)
        db.commit()
        return None

    return router
