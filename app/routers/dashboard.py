from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    Client,
    Delivery,
    FinancialEntry,
    Product,
    ProductionOrder,
    Quote,
    Supplier,
    TechnicalSheet,
)
from app.schemas import DashboardSummary


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)],
)


def count(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    active_orders = int(
        db.scalar(
            select(func.count())
            .select_from(ProductionOrder)
            .where(ProductionOrder.status != "Concluída")
        )
        or 0
    )
    deliveries_today = int(
        db.scalar(
            select(func.count())
            .select_from(Delivery)
            .where(Delivery.scheduled_date == date.today())
        )
        or 0
    )
    receivables = db.scalar(
        select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(
            FinancialEntry.kind == "Receita"
        )
    ) or Decimal("0")
    payables = db.scalar(
        select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(
            FinancialEntry.kind == "Despesa"
        )
    ) or Decimal("0")

    return DashboardSummary(
        clients=count(db, Client),
        suppliers=count(db, Supplier),
        products=count(db, Product),
        technical_sheets=count(db, TechnicalSheet),
        production_orders=count(db, ProductionOrder),
        active_production_orders=active_orders,
        deliveries=count(db, Delivery),
        deliveries_today=deliveries_today,
        quotes=count(db, Quote),
        receivables=receivables,
        payables=payables,
    )
