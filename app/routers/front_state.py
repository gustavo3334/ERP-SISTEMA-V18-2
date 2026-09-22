from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import FrontState, FrontStateRevision
from app.schemas import (
    FrontStatePayload,
    FrontStateRead,
    FrontStateRevisionRead,
)


router = APIRouter(
    prefix="/front-state",
    tags=["Persistência universal do front-end"],
    dependencies=[Depends(get_current_user)],
)


def _read_state(state: FrontState | None, state_key: str) -> FrontStateRead:
    if state is None:
        return FrontStateRead(
            state_key=state_key,
            payload={},
            version=1,
            revision=0,
            updated_at=None,
        )
    return FrontStateRead(
        state_key=state.state_key,
        payload=state.payload or {},
        version=state.version,
        revision=state.revision,
        updated_at=state.updated_at,
    )


def _append_revision(db: Session, state: FrontState) -> None:
    db.add(
        FrontStateRevision(
            state_key=state.state_key,
            revision=state.revision,
            payload=state.payload or {},
            version=state.version,
        )
    )


@router.get("/{state_key}", response_model=FrontStateRead)
def get_state(state_key: str, db: Session = Depends(get_db)):
    state = db.scalar(select(FrontState).where(FrontState.state_key == state_key))
    return _read_state(state, state_key)


@router.put("/{state_key}", response_model=FrontStateRead)
def save_state(
    state_key: str,
    payload: FrontStatePayload,
    db: Session = Depends(get_db),
):
    state = db.scalar(select(FrontState).where(FrontState.state_key == state_key))

    if state is None:
        # A primeira gravação parte da revisão zero. Se o cliente informar outra
        # revisão-base, há um estado inconsistente e não devemos gravar por cima.
        if payload.base_revision not in (None, 0):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "FRONT_STATE_REVISION_CONFLICT",
                    "message": "O estado do servidor mudou. Recarregue os dados antes de salvar.",
                    "server_revision": 0,
                },
            )
        state = FrontState(
            state_key=state_key,
            payload=payload.payload,
            version=payload.version,
            revision=1,
        )
        db.add(state)
        db.flush()
        _append_revision(db, state)
    else:
        # Controle de concorrência otimista: um computador/aba desatualizado não
        # pode apagar ou substituir silenciosamente um snapshot mais recente.
        if payload.base_revision is not None and payload.base_revision != state.revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "FRONT_STATE_REVISION_CONFLICT",
                    "message": "Existem dados mais novos no servidor. Recarregue antes de salvar.",
                    "server_revision": state.revision,
                },
            )
        state.payload = payload.payload
        state.version = payload.version
        state.revision += 1
        db.flush()
        _append_revision(db, state)

    db.commit()
    db.refresh(state)
    return _read_state(state, state_key)


@router.get(
    "/{state_key}/revisions",
    response_model=list[FrontStateRevisionRead],
)
def list_revisions(
    state_key: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(FrontStateRevision)
        .where(FrontStateRevision.state_key == state_key)
        .order_by(desc(FrontStateRevision.revision))
        .limit(limit)
    ).all()
    return [
        FrontStateRevisionRead(
            state_key=row.state_key,
            revision=row.revision,
            payload=row.payload or {},
            version=row.version,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post(
    "/{state_key}/restore/{revision}",
    response_model=FrontStateRead,
)
def restore_revision(
    state_key: str,
    revision: int,
    db: Session = Depends(get_db),
):
    historic = db.scalar(
        select(FrontStateRevision).where(
            FrontStateRevision.state_key == state_key,
            FrontStateRevision.revision == revision,
        )
    )
    if historic is None:
        raise HTTPException(status_code=404, detail="Revisão não encontrada.")

    state = db.scalar(select(FrontState).where(FrontState.state_key == state_key))
    if state is None:
        state = FrontState(
            state_key=state_key,
            payload=historic.payload or {},
            version=historic.version,
            revision=1,
        )
        db.add(state)
    else:
        state.payload = historic.payload or {}
        state.version = historic.version
        state.revision += 1

    db.flush()
    _append_revision(db, state)
    db.commit()
    db.refresh(state)
    return _read_state(state, state_key)
