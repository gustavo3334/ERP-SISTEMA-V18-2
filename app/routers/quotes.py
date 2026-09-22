from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import Quote, QuoteItem
from app.schemas import QuoteCreate, QuoteRead, QuoteUpdate
from app.services import calculate_quote_item, generate_code


router = APIRouter(
    prefix="/quotes",
    tags=["Vendas e orçamentos"],
    dependencies=[Depends(get_current_user)],
)


def load_quote(db: Session, quote_id: str) -> Quote | None:
    return db.scalar(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.items))
    )


def replace_items(db: Session, quote: Quote, inputs) -> None:
    for item in list(quote.items):
        db.delete(item)
    db.flush()

    total = Decimal("0")
    for input_item in inputs:
        item_total = calculate_quote_item(input_item)
        total += item_total
        db.add(
            QuoteItem(
                quote_id=quote.id,
                product_id=input_item.product_id,
                product_name=input_item.product_name,
                quantity=input_item.quantity,
                unit_price=input_item.unit_price,
                discount=input_item.discount,
                total=item_total,
            )
        )
    quote.total = total


@router.get("", response_model=list[QuoteRead], dependencies=[Depends(require_permission("sales.read"))])
def list_quotes(db: Session = Depends(get_db)):
    statement = (
        select(Quote)
        .options(selectinload(Quote.items))
        .order_by(Quote.created_at.desc())
    )
    return list(db.scalars(statement).unique().all())


@router.get("/{quote_id}", response_model=QuoteRead, dependencies=[Depends(require_permission("sales.read"))])
def get_quote(quote_id: str, db: Session = Depends(get_db)):
    quote = load_quote(db, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    return quote


@router.post("", response_model=QuoteRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sales.write"))])
def create_quote(payload: QuoteCreate, db: Session = Depends(get_db)):
    quote = Quote(
        code=generate_code("ORC"),
        client_id=payload.client_id,
        client_name=payload.client_name,
        valid_until=payload.valid_until,
        probability=payload.probability,
        payment_method=payload.payment_method,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(quote)
    db.flush()
    replace_items(db, quote, payload.items)
    db.commit()
    return load_quote(db, quote.id)


@router.put("/{quote_id}", response_model=QuoteRead, dependencies=[Depends(require_permission("sales.write"))])
def update_quote(
    quote_id: str,
    payload: QuoteUpdate,
    db: Session = Depends(get_db),
):
    quote = load_quote(db, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    for key, value in payload.model_dump(
        exclude_unset=True,
        exclude={"items"},
    ).items():
        setattr(quote, key, value)

    if payload.items is not None:
        replace_items(db, quote, payload.items)

    db.commit()
    return load_quote(db, quote.id)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("sales.write"))])
def delete_quote(quote_id: str, db: Session = Depends(get_db)):
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    db.delete(quote)
    db.commit()
    return None
