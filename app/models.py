from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    password_hash: Mapped[str] = mapped_column(String(500), default="")
    role: Mapped[str] = mapped_column(String(60), default="administrator")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    branch_id: Mapped[str | None] = mapped_column(
        ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legacy_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    document: Mapped[str] = mapped_column(String(30), default="", index=True)
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="Ativo", index=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    preferred_payment: Mapped[str] = mapped_column(String(80), default="")
    payment_methods_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    purchase_history: Mapped[str] = mapped_column(Text, default="")
    front_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ClientProductPrice(Base, TimestampMixin):
    __tablename__ = "client_product_prices"
    __table_args__ = (
        UniqueConstraint("client_id", "product_ref", name="uq_client_product_price_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    product_ref: Mapped[str] = mapped_column(String(120), index=True)
    product_name: Mapped[str] = mapped_column(String(220), default="")
    price: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legal_name: Mapped[str] = mapped_column(String(220), index=True)
    trade_name: Mapped[str] = mapped_column(String(200), default="")
    document: Mapped[str] = mapped_column(String(30), default="", index=True)
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), index=True)
    item_type: Mapped[str] = mapped_column(String(60), default="Produto acabado")
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StockLocation(Base, TimestampMixin):
    __tablename__ = "stock_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), index=True)
    warehouse: Mapped[str] = mapped_column(String(120), default="")
    aisle: Mapped[str] = mapped_column(String(60), default="")
    rack: Mapped[str] = mapped_column(String(60), default="")
    shelf: Mapped[str] = mapped_column(String(60), default="")
    address_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(220), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    item_type: Mapped[str] = mapped_column(String(60), default="Produto acabado")

    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    supplier_id: Mapped[str | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[str | None] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="SET NULL"), nullable=True
    )

    color: Mapped[str] = mapped_column(String(100), default="")
    size: Mapped[str] = mapped_column(String(100), default="")
    unit: Mapped[str] = mapped_column(String(30), default="UN")

    cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    technical_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    reserved_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    base_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)

    manufacturing_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    barcode: Mapped[str] = mapped_column(String(120), default="")
    color: Mapped[str] = mapped_column(String(100), default="")
    size: Mapped[str] = mapped_column(String(100), default="")
    supplier_id: Mapped[str | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[str | None] = mapped_column(
        ForeignKey("stock_locations.id", ondelete="SET NULL"), nullable=True
    )
    stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    reserved_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    product: Mapped[Product] = relationship(back_populates="variants")


class TechnicalSheet(Base, TimestampMixin):
    __tablename__ = "technical_sheets"
    __table_args__ = (
        UniqueConstraint("product_id", "version", name="uq_sheet_product_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(120), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped[Product] = relationship()
    stages: Mapped[list["TechnicalStage"]] = relationship(
        back_populates="sheet",
        cascade="all, delete-orphan",
        order_by="TechnicalStage.step_order",
    )
    items: Mapped[list["TechnicalSheetItem"]] = relationship(
        back_populates="sheet",
        cascade="all, delete-orphan",
    )


class TechnicalStage(Base, TimestampMixin):
    __tablename__ = "technical_stages"
    __table_args__ = (
        UniqueConstraint("sheet_id", "step_order", name="uq_sheet_stage_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sheet_id: Mapped[str] = mapped_column(
        ForeignKey("technical_sheets.id", ondelete="CASCADE"), index=True
    )
    step_order: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(180))
    sector: Mapped[str] = mapped_column(String(160), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    setup_minutes: Mapped[int] = mapped_column(Integer, default=0)
    operation_minutes: Mapped[int] = mapped_column(Integer, default=0)
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    machine_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    overhead_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    loss_percent: Mapped[Decimal] = mapped_column(Numeric(7, 3), default=0)

    sheet: Mapped[TechnicalSheet] = relationship(back_populates="stages")
    items: Mapped[list["TechnicalSheetItem"]] = relationship(
        back_populates="stage"
    )
    checklist: Mapped[list["TechnicalChecklist"]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
    )


class TechnicalSheetItem(Base, TimestampMixin):
    __tablename__ = "technical_sheet_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sheet_id: Mapped[str] = mapped_column(
        ForeignKey("technical_sheets.id", ondelete="CASCADE"), index=True
    )
    stage_id: Mapped[str | None] = mapped_column(
        ForeignKey("technical_stages.id", ondelete="SET NULL"), nullable=True
    )
    component_product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    item_kind: Mapped[str] = mapped_column(String(40), default="Matéria-prima")
    code: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(220))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    unit: Mapped[str] = mapped_column(String(30), default="UN")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    sheet: Mapped[TechnicalSheet] = relationship(back_populates="items")
    stage: Mapped[TechnicalStage | None] = relationship(back_populates="items")


class TechnicalChecklist(Base, TimestampMixin):
    __tablename__ = "technical_checklists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    stage_id: Mapped[str] = mapped_column(
        ForeignKey("technical_stages.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=True)

    stage: Mapped[TechnicalStage] = relationship(back_populates="checklist")


class ProductionOrder(Base, TimestampMixin):
    __tablename__ = "production_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    order_ref: Mapped[str] = mapped_column(String(100), default="")
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    technical_sheet_id: Mapped[str | None] = mapped_column(
        ForeignKey("technical_sheets.id", ondelete="SET NULL"), nullable=True
    )
    production_mode: Mapped[str] = mapped_column(
        String(60), default="PRODUZIR_DO_ZERO", index=True
    )
    source_stock_product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    source_stock_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), default=0
    )
    source_stock_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0
    )
    product_name: Mapped[str] = mapped_column(String(220))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=1)
    responsible: Mapped[str] = mapped_column(String(160), default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    forecast_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    workflow_stage: Mapped[str] = mapped_column(String(60), default="Novo pedido")
    progress: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    status: Mapped[str] = mapped_column(String(60), default="Pendente")
    priority: Mapped[str] = mapped_column(String(30), default="Normal")
    planned_material_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    planned_process_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    stages: Mapped[list["ProductionOrderStage"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="ProductionOrderStage.step_order",
    )


class ProductionOrderStage(Base, TimestampMixin):
    __tablename__ = "production_order_stages"
    __table_args__ = (
        UniqueConstraint("order_id", "step_order", name="uq_order_stage_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("production_orders.id", ondelete="CASCADE"), index=True
    )
    template_stage_id: Mapped[str | None] = mapped_column(
        ForeignKey("technical_stages.id", ondelete="SET NULL"), nullable=True
    )
    step_order: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(180))
    sector: Mapped[str] = mapped_column(String(160), default="")
    responsible: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(60), default="Pendente")

    planned_material_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    planned_labor_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    planned_machine_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    planned_overhead_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    actual_material_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    actual_labor_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    actual_machine_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    actual_overhead_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    loss_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    order: Mapped[ProductionOrder] = relationship(back_populates="stages")
    items: Mapped[list["ProductionOrderStageItem"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )
    checklist: Mapped[list["ProductionOrderChecklist"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )


class ProductionOrderStageItem(Base, TimestampMixin):
    __tablename__ = "production_order_stage_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    stage_id: Mapped[str] = mapped_column(
        ForeignKey("production_order_stages.id", ondelete="CASCADE"), index=True
    )
    item_kind: Mapped[str] = mapped_column(String(40), default="Matéria-prima")
    code: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(220))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    unit: Mapped[str] = mapped_column(String(30), default="UN")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)

    stage: Mapped[ProductionOrderStage] = relationship(back_populates="items")


class ProductionOrderChecklist(Base, TimestampMixin):
    __tablename__ = "production_order_checklists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    stage_id: Mapped[str] = mapped_column(
        ForeignKey("production_order_stages.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    done: Mapped[bool] = mapped_column(Boolean, default=False)

    stage: Mapped[ProductionOrderStage] = relationship(back_populates="checklist")


class Delivery(Base, TimestampMixin):
    __tablename__ = "deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    client_id: Mapped[str | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    order_ref: Mapped[str] = mapped_column(String(100), default="")
    recipient_name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(Text)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    route_name: Mapped[str] = mapped_column(String(160), default="")
    driver_name: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(60), default="Agendada")
    occurrence: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class Quote(Base, TimestampMixin):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    client_id: Mapped[str | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    client_name: Mapped[str] = mapped_column(String(200), default="")
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    probability: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    payment_method: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(60), default="Rascunho")
    notes: Mapped[str] = mapped_column(Text, default="")
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    items: Mapped[list["QuoteItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )


class QuoteItem(Base, TimestampMixin):
    __tablename__ = "quote_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    quote_id: Mapped[str] = mapped_column(
        ForeignKey("quotes.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(220))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    quote: Mapped[Quote] = relationship(back_populates="items")


class FinancialEntry(Base, TimestampMixin):
    __tablename__ = "financial_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(30), default="Receita")
    description: Mapped[str] = mapped_column(String(220))
    category: Mapped[str] = mapped_column(String(120), default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    status: Mapped[str] = mapped_column(String(60), default="A vencer")
    notes: Mapped[str] = mapped_column(Text, default="")


class FrontState(Base, TimestampMixin):
    __tablename__ = "front_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    state_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FrontStateRevision(Base):
    __tablename__ = "front_state_revisions"
    __table_args__ = (
        UniqueConstraint("state_key", "revision", name="uq_front_state_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    state_key: Mapped[str] = mapped_column(String(120), index=True)
    revision: Mapped[int] = mapped_column(Integer, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
