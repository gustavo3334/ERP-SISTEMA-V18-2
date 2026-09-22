from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import TechnicalSheet, TechnicalStage
from app.schemas import (
    TechnicalSheetCreate,
    TechnicalSheetRead,
    TechnicalSheetUpdate,
)
from app.services import (
    build_technical_sheet,
    load_technical_sheet,
    recalculate_product_technical_cost,
    replace_technical_sheet_structure,
)


router = APIRouter(
    prefix="/technical-sheets",
    tags=["Ficha técnica PCP"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[TechnicalSheetRead], dependencies=[Depends(require_permission("pcp.read"))])
def list_sheets(db: Session = Depends(get_db)):
    statement = (
        select(TechnicalSheet)
        .options(
            selectinload(TechnicalSheet.items),
            selectinload(TechnicalSheet.stages).selectinload(
                TechnicalStage.checklist
            ),
        )
        .order_by(TechnicalSheet.created_at.desc())
    )
    return list(db.scalars(statement).unique().all())


@router.get("/{sheet_id}", response_model=TechnicalSheetRead, dependencies=[Depends(require_permission("pcp.read"))])
def get_sheet(sheet_id: str, db: Session = Depends(get_db)):
    sheet = load_technical_sheet(db, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Ficha técnica não encontrada.")
    return sheet


@router.post(
    "",
    response_model=TechnicalSheetRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("pcp.write"))],
)
def create_sheet(payload: TechnicalSheetCreate, db: Session = Depends(get_db)):
    try:
        sheet = build_technical_sheet(db, payload)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma ficha com esta versão para o produto.",
        ) from exc
    return load_technical_sheet(db, sheet.id)


@router.put("/{sheet_id}", response_model=TechnicalSheetRead, dependencies=[Depends(require_permission("pcp.write"))])
def update_sheet(
    sheet_id: str,
    payload: TechnicalSheetUpdate,
    db: Session = Depends(get_db),
):
    sheet = load_technical_sheet(db, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Ficha técnica não encontrada.")

    simple_data = payload.model_dump(
        exclude_unset=True,
        exclude={"stages", "items"},
    )
    for key, value in simple_data.items():
        setattr(sheet, key, value)

    if payload.stages is not None or payload.items is not None:
        replace_technical_sheet_structure(
            db,
            sheet,
            payload.stages or [],
            payload.items or [],
        )
    else:
        recalculate_product_technical_cost(db, sheet)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A versão informada já existe para este produto.",
        ) from exc
    return load_technical_sheet(db, sheet.id)


@router.delete("/{sheet_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("pcp.write"))])
def delete_sheet(sheet_id: str, db: Session = Depends(get_db)):
    sheet = db.get(TechnicalSheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Ficha técnica não encontrada.")
    db.delete(sheet)
    db.commit()
    return None
