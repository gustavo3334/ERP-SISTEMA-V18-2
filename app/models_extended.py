from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AccessProfile(Base, TimestampMixin):
    __tablename__ = "access_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AccessProfilePermission(Base):
    __tablename__ = "access_profile_permissions"
    profile_id: Mapped[str] = mapped_column(ForeignKey("access_profiles.id", ondelete="CASCADE"), primary_key=True)
    permission: Mapped[str] = mapped_column(String(140), primary_key=True)


class UserAccessProfile(Base):
    __tablename__ = "user_access_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("access_profiles.id", ondelete="CASCADE"), index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_name: Mapped[str] = mapped_column(String(180), default="")
    module: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(100), default="", index=True)
    entity_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    before_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str] = mapped_column(String(80), default="")


class StockBalance(Base, TimestampMixin):
    __tablename__ = "stock_balances"
    __table_args__ = (UniqueConstraint("product_id", "variant_id", "location_id", name="uq_stock_product_variant_location"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[str | None] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("stock_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=0)
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=0)


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    variant_id: Mapped[str | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("stock_locations.id", ondelete="SET NULL"), nullable=True)
    movement_type: Mapped[str] = mapped_column(String(50), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    reference_type: Mapped[str] = mapped_column(String(80), default="", index=True)
    reference_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date, default=date.today)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Rascunho", index=True)
    payment_terms: Mapped[str] = mapped_column(String(160), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    freight: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    items: Mapped[list["PurchaseOrderItem"]] = orm_relationship(back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base, TimestampMixin):
    __tablename__ = "purchase_order_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    description: Mapped[str] = mapped_column(String(240), default="")
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=0)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("stock_locations.id", ondelete="SET NULL"), nullable=True)
    order: Mapped[PurchaseOrder] = orm_relationship(back_populates="items")


class SalesOrder(Base, TimestampMixin):
    __tablename__ = "sales_orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    client_name: Mapped[str] = mapped_column(String(220), default="")
    issue_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(60), default="Rascunho", index=True)
    payment_method: Mapped[str] = mapped_column(String(100), default="")
    delivery_address: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    freight: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    items: Mapped[list["SalesOrderItem"]] = orm_relationship(back_populates="order", cascade="all, delete-orphan")


class SalesOrderItem(Base, TimestampMixin):
    __tablename__ = "sales_order_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("sales_orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    description: Mapped[str] = mapped_column(String(240), default="")
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    production_order_id: Mapped[str | None] = mapped_column(ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True)
    order: Mapped[SalesOrder] = orm_relationship(back_populates="items")


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legacy_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(220), index=True)
    social_name: Mapped[str] = mapped_column(String(220), default="")
    collaborator_model: Mapped[str] = mapped_column(String(40), default="Pessoa física")
    employment_category: Mapped[str] = mapped_column(String(60), default="Registrado", index=True)
    employee_type: Mapped[str] = mapped_column(String(60), default="Operacional", index=True)
    status: Mapped[str] = mapped_column(String(50), default="Ativo", index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str] = mapped_column(String(40), default="")
    marital_status: Mapped[str] = mapped_column(String(60), default="")
    nationality: Mapped[str] = mapped_column(String(100), default="")
    naturality: Mapped[str] = mapped_column(String(120), default="")
    mother_name: Mapped[str] = mapped_column(String(220), default="")
    father_name: Mapped[str] = mapped_column(String(220), default="")
    cpf: Mapped[str] = mapped_column(String(30), default="", index=True)
    rg: Mapped[str] = mapped_column(String(40), default="")
    rg_issuer: Mapped[str] = mapped_column(String(80), default="")
    rg_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    voter_title: Mapped[str] = mapped_column(String(60), default="")
    voter_zone: Mapped[str] = mapped_column(String(30), default="")
    voter_section: Mapped[str] = mapped_column(String(30), default="")
    pis: Mapped[str] = mapped_column(String(40), default="")
    ctps: Mapped[str] = mapped_column(String(60), default="")
    cnh: Mapped[str] = mapped_column(String(60), default="")
    cnh_category: Mapped[str] = mapped_column(String(20), default="")
    cnh_validity: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str] = mapped_column(String(255), default="")
    phone_primary: Mapped[str] = mapped_column(String(50), default="")
    phone_secondary: Mapped[str] = mapped_column(String(50), default="")
    photo_url: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[str] = mapped_column(String(140), default="")
    sector: Mapped[str] = mapped_column(String(140), default="", index=True)
    work_schedule: Mapped[str] = mapped_column(String(120), default="")
    scale: Mapped[str] = mapped_column(String(80), default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    salary: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    fixed_bonus: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    variable_bonus: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    advance_percent: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=0)
    benefits_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    front_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    address: Mapped["EmployeeAddress | None"] = orm_relationship(back_populates="employee", uselist=False, cascade="all, delete-orphan")
    contacts: Mapped[list["EmployeeContact"]] = orm_relationship(back_populates="employee", cascade="all, delete-orphan")
    health: Mapped["EmployeeHealth | None"] = orm_relationship(back_populates="employee", uselist=False, cascade="all, delete-orphan")
    mei: Mapped["EmployeeMEI | None"] = orm_relationship(back_populates="employee", uselist=False, cascade="all, delete-orphan")
    dependents: Mapped[list["EmployeeDependent"]] = orm_relationship(back_populates="employee", cascade="all, delete-orphan")
    bank_accounts: Mapped[list["EmployeeBankAccount"]] = orm_relationship(back_populates="employee", cascade="all, delete-orphan")
    bonuses: Mapped[list["EmployeeBonus"]] = orm_relationship(back_populates="employee", cascade="all, delete-orphan")
    transport_plan: Mapped["EmployeeTransportPlan | None"] = orm_relationship(back_populates="employee", uselist=False, cascade="all, delete-orphan")
    piece_rates: Mapped[list["EmployeePieceRate"]] = orm_relationship(back_populates="employee", cascade="all, delete-orphan")
    production_entries: Mapped[list["EmployeeProductionEntry"]] = orm_relationship(back_populates="employee", cascade="all, delete-orphan")


class EmployeeAddress(Base, TimestampMixin):
    __tablename__ = "employee_addresses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), unique=True, index=True)
    cep: Mapped[str] = mapped_column(String(20), default="")
    street: Mapped[str] = mapped_column(String(220), default="")
    number: Mapped[str] = mapped_column(String(40), default="")
    complement: Mapped[str] = mapped_column(String(180), default="")
    neighborhood: Mapped[str] = mapped_column(String(160), default="")
    city: Mapped[str] = mapped_column(String(160), default="")
    state: Mapped[str] = mapped_column(String(20), default="")
    residence_type: Mapped[str] = mapped_column(String(40), default="Casa")
    house_unit: Mapped[str] = mapped_column(String(80), default="")
    apartment: Mapped[str] = mapped_column(String(40), default="")
    block: Mapped[str] = mapped_column(String(40), default="")
    floor: Mapped[str] = mapped_column(String(40), default="")
    condominium: Mapped[str] = mapped_column(String(180), default="")
    employee: Mapped[Employee] = orm_relationship(back_populates="address")


class EmployeeContact(Base, TimestampMixin):
    __tablename__ = "employee_contacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    contact_type: Mapped[str] = mapped_column(String(40), default="Emergência")
    name: Mapped[str] = mapped_column(String(180), default="")
    relationship: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    employee: Mapped[Employee] = orm_relationship(back_populates="contacts")


class EmployeeHealth(Base, TimestampMixin):
    __tablename__ = "employee_health"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), unique=True, index=True)
    blood_type: Mapped[str] = mapped_column(String(30), default="")
    has_disease: Mapped[bool] = mapped_column(Boolean, default=False)
    conditions: Mapped[str] = mapped_column(Text, default="")
    under_treatment: Mapped[bool] = mapped_column(Boolean, default=False)
    treatment: Mapped[str] = mapped_column(Text, default="")
    continuous_medication: Mapped[bool] = mapped_column(Boolean, default=False)
    medication: Mapped[str] = mapped_column(Text, default="")
    dosage: Mapped[str] = mapped_column(String(120), default="")
    medication_schedule: Mapped[str] = mapped_column(String(180), default="")
    allergies: Mapped[str] = mapped_column(Text, default="")
    drug_allergies: Mapped[str] = mapped_column(Text, default="")
    restrictions: Mapped[str] = mapped_column(Text, default="")
    special_need: Mapped[str] = mapped_column(Text, default="")
    health_plan: Mapped[str] = mapped_column(String(180), default="")
    doctor: Mapped[str] = mapped_column(String(180), default="")
    can_provide_medication: Mapped[bool] = mapped_column(Boolean, default=False)
    authorized_medication: Mapped[str] = mapped_column(Text, default="")
    emergency_notes: Mapped[str] = mapped_column(Text, default="")
    employee: Mapped[Employee] = orm_relationship(back_populates="health")


class EmployeeMEI(Base, TimestampMixin):
    __tablename__ = "employee_mei"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), unique=True, index=True)
    cnpj: Mapped[str] = mapped_column(String(30), default="", index=True)
    legal_name: Mapped[str] = mapped_column(String(220), default="")
    trade_name: Mapped[str] = mapped_column(String(220), default="")
    municipal_registration: Mapped[str] = mapped_column(String(80), default="")
    employee: Mapped[Employee] = orm_relationship(back_populates="mei")


class EmployeeDependent(Base, TimestampMixin):
    __tablename__ = "employee_dependents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legacy_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(220))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cpf: Mapped[str] = mapped_column(String(30), default="")
    relationship: Mapped[str] = mapped_column(String(80), default="Filho(a)")
    ir_dependent: Mapped[bool] = mapped_column(Boolean, default=False)
    employee: Mapped[Employee] = orm_relationship(back_populates="dependents")
    alimony: Mapped["EmployeeAlimony | None"] = orm_relationship(back_populates="dependent", uselist=False, cascade="all, delete-orphan")


class EmployeeAlimony(Base, TimestampMixin):
    __tablename__ = "employee_alimony"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dependent_id: Mapped[str] = mapped_column(ForeignKey("employee_dependents.id", ondelete="CASCADE"), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    agreement_type: Mapped[str] = mapped_column(String(60), default="")
    calculation_type: Mapped[str] = mapped_column(String(40), default="Valor fixo")
    fixed_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    percentage: Mapped[Decimal] = mapped_column(Numeric(8, 3), default=0)
    beneficiary: Mapped[str] = mapped_column(String(220), default="")
    bank: Mapped[str] = mapped_column(String(120), default="")
    agency: Mapped[str] = mapped_column(String(60), default="")
    account: Mapped[str] = mapped_column(String(80), default="")
    pix_key: Mapped[str] = mapped_column(String(220), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    dependent: Mapped[EmployeeDependent] = orm_relationship(back_populates="alimony")


class EmployeeBankAccount(Base, TimestampMixin):
    __tablename__ = "employee_bank_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    bank: Mapped[str] = mapped_column(String(140), default="")
    bank_code: Mapped[str] = mapped_column(String(20), default="")
    agency: Mapped[str] = mapped_column(String(60), default="")
    account: Mapped[str] = mapped_column(String(80), default="")
    account_digit: Mapped[str] = mapped_column(String(20), default="")
    account_type: Mapped[str] = mapped_column(String(60), default="Conta corrente")
    holder: Mapped[str] = mapped_column(String(220), default="")
    holder_document: Mapped[str] = mapped_column(String(40), default="")
    pix_type: Mapped[str] = mapped_column(String(40), default="")
    pix_key: Mapped[str] = mapped_column(String(220), default="")
    pix_institution: Mapped[str] = mapped_column(String(160), default="")
    portability: Mapped[bool] = mapped_column(Boolean, default=False)
    origin_bank: Mapped[str] = mapped_column(String(160), default="")
    destination_bank: Mapped[str] = mapped_column(String(160), default="")
    receiving_bank: Mapped[str] = mapped_column(String(160), default="")
    salary_payment: Mapped[str] = mapped_column(String(80), default="Crédito em conta")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    employee: Mapped[Employee] = orm_relationship(back_populates="bank_accounts")


class EmployeeBonus(Base, TimestampMixin):
    __tablename__ = "employee_bonuses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legacy_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    bonus_type: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    competence: Mapped[str] = mapped_column(String(20), default="")
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    employee: Mapped[Employee] = orm_relationship(back_populates="bonuses")


class EmployeeTransportPlan(Base, TimestampMixin):
    __tablename__ = "employee_transport_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), unique=True, index=True)
    company_address: Mapped[str] = mapped_column(Text, default="")
    employee_address: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(100), default="")
    distance_km: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    round_trip_distance_km: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    round_trip_duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    working_days: Mapped[int] = mapped_column(Integer, default=0)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    monthly_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    route_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    employee: Mapped[Employee] = orm_relationship(back_populates="transport_plan")
    legs: Mapped[list["EmployeeTransportLeg"]] = orm_relationship(back_populates="plan", cascade="all, delete-orphan")


class EmployeeTransportLeg(Base, TimestampMixin):
    __tablename__ = "employee_transport_legs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    plan_id: Mapped[str] = mapped_column(ForeignKey("employee_transport_plans.id", ondelete="CASCADE"), index=True)
    transport_type: Mapped[str] = mapped_column(String(60), default="Ônibus")
    line: Mapped[str] = mapped_column(String(120), default="")
    origin: Mapped[str] = mapped_column(String(180), default="")
    destination: Mapped[str] = mapped_column(String(180), default="")
    fare: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    uses_per_day: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    plan: Mapped[EmployeeTransportPlan] = orm_relationship(back_populates="legs")


class EmployeePieceRate(Base, TimestampMixin):
    __tablename__ = "employee_piece_rates"
    __table_args__ = (Index("ix_piece_rate_lookup", "employee_id", "sector", "operation", "product_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legacy_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    sector: Mapped[str] = mapped_column(String(120), default="")
    operation: Mapped[str] = mapped_column(String(160), default="")
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(220), default="")
    rate: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=0)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    employee: Mapped[Employee] = orm_relationship(back_populates="piece_rates")


class EmployeeProductionEntry(Base, TimestampMixin):
    __tablename__ = "employee_production_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legacy_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    production_order_id: Mapped[str | None] = mapped_column(ForeignKey("production_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    production_order_ref: Mapped[str] = mapped_column(String(100), default="")
    entry_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    sector: Mapped[str] = mapped_column(String(120), default="")
    operation: Mapped[str] = mapped_column(String(160), default="")
    product_name: Mapped[str] = mapped_column(String(220), default="")
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), default=0)
    rate: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    employee: Mapped[Employee] = orm_relationship(back_populates="production_entries")


class EmployeePayrollStatement(Base, TimestampMixin):
    __tablename__ = "employee_payroll_statements"
    __table_args__ = (UniqueConstraint("employee_id", "competence", name="uq_payroll_employee_competence"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    competence: Mapped[str] = mapped_column(String(20), index=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    bonuses: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    piece_production: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    transport: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    advances: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    other_additions: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    other_discounts: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    gross: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    net: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(50), default="Calculado")


class EmployeeAdvance(Base, TimestampMixin):
    __tablename__ = "employee_advances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    competence: Mapped[str] = mapped_column(String(20), index=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    status: Mapped[str] = mapped_column(String(50), default="Pendente")


class StoredFile(Base, TimestampMixin):
    __tablename__ = "stored_files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(100), default="Outro", index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(120), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    storage_path: Mapped[str] = mapped_column(Text)
    # Cópia persistente no PostgreSQL. O filesystem do Render Free é efêmero;
    # o blob garante que o documento continue disponível após restart/deploy.
    content_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class EmployeeDocumentRecord(Base, TimestampMixin):
    __tablename__ = "employee_document_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legacy_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    stored_file_id: Mapped[str | None] = mapped_column(ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True)
    document_type: Mapped[str] = mapped_column(String(120), default="Outro")
    document_number: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(60), default="Recebido")
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    setting_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
