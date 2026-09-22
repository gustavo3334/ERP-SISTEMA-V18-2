from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field


class StockMovementCreate(BaseModel):
    product_id: str
    variant_id: str | None = None
    location_id: str | None = None
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal = Decimal("0")
    reference_type: str = ""
    reference_id: str = ""
    notes: str = ""




class StockTransferRequest(BaseModel):
    product_id: str
    quantity: Decimal
    source_location_id: str
    destination_location_id: str
    variant_id: str | None = None
    notes: str = ""

class ReservationRequest(BaseModel):
    product_id: str
    quantity: Decimal
    location_id: str | None = None
    reference_type: str = ""
    reference_id: str = ""


class PurchaseItemInput(BaseModel):
    product_id: str
    description: str = ""
    quantity: Decimal
    unit_cost: Decimal
    location_id: str | None = None


class PurchaseOrderCreate(BaseModel):
    supplier_id: str | None = None
    expected_date: date | None = None
    payment_terms: str = ""
    notes: str = ""
    discount: Decimal = Decimal("0")
    freight: Decimal = Decimal("0")
    items: list[PurchaseItemInput] = Field(default_factory=list)


class ReceivePurchaseItem(BaseModel):
    item_id: str
    quantity: Decimal


class ReceivePurchaseRequest(BaseModel):
    items: list[ReceivePurchaseItem] = Field(default_factory=list)
    create_payable: bool = True


class SalesItemInput(BaseModel):
    product_id: str
    description: str = ""
    quantity: Decimal
    unit_price: Decimal | None = None
    discount_percent: Decimal = Decimal("0")


class SalesOrderCreate(BaseModel):
    client_id: str | None = None
    client_name: str = ""
    payment_method: str = ""
    delivery_address: str = ""
    notes: str = ""
    discount: Decimal = Decimal("0")
    freight: Decimal = Decimal("0")
    items: list[SalesItemInput] = Field(default_factory=list)


class SalesConfirmRequest(BaseModel):
    auto_create_production: bool = True
    create_receivable: bool = True


class EmployeeAddressInput(BaseModel):
    cep: str = ""
    street: str = ""
    number: str = ""
    complement: str = ""
    neighborhood: str = ""
    city: str = ""
    state: str = ""
    residence_type: str = "Casa"
    house_unit: str = ""
    apartment: str = ""
    block: str = ""
    floor: str = ""
    condominium: str = ""


class EmployeeContactInput(BaseModel):
    contact_type: str = "Emergência"
    name: str = ""
    relationship: str = ""
    phone: str = ""
    priority: int = 1


class EmployeeHealthInput(BaseModel):
    blood_type: str = ""
    has_disease: bool = False
    conditions: str = ""
    under_treatment: bool = False
    treatment: str = ""
    continuous_medication: bool = False
    medication: str = ""
    dosage: str = ""
    medication_schedule: str = ""
    allergies: str = ""
    drug_allergies: str = ""
    restrictions: str = ""
    special_need: str = ""
    health_plan: str = ""
    doctor: str = ""
    can_provide_medication: bool = False
    authorized_medication: str = ""
    emergency_notes: str = ""


class EmployeeMEIInput(BaseModel):
    cnpj: str = ""
    legal_name: str = ""
    trade_name: str = ""
    municipal_registration: str = ""


class AlimonyInput(BaseModel):
    active: bool = True
    agreement_type: str = ""
    calculation_type: str = "Valor fixo"
    fixed_amount: Decimal = Decimal("0")
    percentage: Decimal = Decimal("0")
    beneficiary: str = ""
    bank: str = ""
    agency: str = ""
    account: str = ""
    pix_key: str = ""
    notes: str = ""


class DependentInput(BaseModel):
    legacy_id: str = ""
    name: str
    birth_date: date | None = None
    cpf: str = ""
    relationship: str = "Filho(a)"
    ir_dependent: bool = False
    alimony: AlimonyInput | None = None


class BankAccountInput(BaseModel):
    bank: str = ""
    bank_code: str = ""
    agency: str = ""
    account: str = ""
    account_digit: str = ""
    account_type: str = "Conta corrente"
    holder: str = ""
    holder_document: str = ""
    pix_type: str = ""
    pix_key: str = ""
    pix_institution: str = ""
    portability: bool = False
    origin_bank: str = ""
    destination_bank: str = ""
    receiving_bank: str = ""
    salary_payment: str = "Crédito em conta"
    is_primary: bool = True


class BonusInput(BaseModel):
    legacy_id: str = ""
    bonus_type: str = ""
    description: str = ""
    amount: Decimal = Decimal("0")
    competence: str = ""
    recurring: bool = False
    active: bool = True


class TransportLegInput(BaseModel):
    transport_type: str = "Ônibus"
    line: str = ""
    origin: str = ""
    destination: str = ""
    fare: Decimal = Decimal("0")
    uses_per_day: Decimal = Decimal("0")


class TransportPlanInput(BaseModel):
    company_address: str = ""
    employee_address: str = ""
    provider: str = ""
    distance_km: Decimal = Decimal("0")
    duration_minutes: int = 0
    round_trip_distance_km: Decimal = Decimal("0")
    round_trip_duration_minutes: int = 0
    working_days: int = 0
    reviewed: bool = False
    route_data: dict[str, Any] = Field(default_factory=dict)
    legs: list[TransportLegInput] = Field(default_factory=list)


class EmployeeCreate(BaseModel):
    legacy_id: str = ""
    full_name: str
    social_name: str = ""
    collaborator_model: str = "Pessoa física"
    employment_category: str = "Registrado"
    employee_type: str = "Operacional"
    status: str = "Ativo"
    birth_date: date | None = None
    sex: str = ""
    marital_status: str = ""
    nationality: str = ""
    naturality: str = ""
    mother_name: str = ""
    father_name: str = ""
    cpf: str = ""
    rg: str = ""
    rg_issuer: str = ""
    rg_issue_date: date | None = None
    voter_title: str = ""
    voter_zone: str = ""
    voter_section: str = ""
    pis: str = ""
    ctps: str = ""
    cnh: str = ""
    cnh_category: str = ""
    cnh_validity: date | None = None
    email: str = ""
    phone_primary: str = ""
    phone_secondary: str = ""
    photo_url: str = ""
    position: str = ""
    sector: str = ""
    work_schedule: str = ""
    scale: str = ""
    start_date: date | None = None
    registration_date: date | None = None
    admission_date: date | None = None
    termination_date: date | None = None
    salary: Decimal = Decimal("0")
    fixed_bonus: Decimal = Decimal("0")
    variable_bonus: Decimal = Decimal("0")
    advance_percent: Decimal = Decimal("0")
    benefits: list[Any] = Field(default_factory=list)
    notes: str = ""
    address: EmployeeAddressInput | None = None
    contacts: list[EmployeeContactInput] = Field(default_factory=list)
    health: EmployeeHealthInput | None = None
    mei: EmployeeMEIInput | None = None
    dependents: list[DependentInput] = Field(default_factory=list)
    bank_accounts: list[BankAccountInput] = Field(default_factory=list)
    bonuses: list[BonusInput] = Field(default_factory=list)
    transport_plan: TransportPlanInput | None = None


class PieceRateInput(BaseModel):
    legacy_id: str = ""
    employee_id: str
    sector: str = ""
    operation: str = ""
    product_id: str | None = None
    product_name: str = ""
    rate: Decimal = Decimal("0")
    valid_from: date | None = None
    valid_until: date | None = None
    active: bool = True


class ProductionEntryInput(BaseModel):
    legacy_id: str = ""
    employee_id: str
    production_order_id: str | None = None
    production_order_ref: str = ""
    entry_date: date
    sector: str = ""
    operation: str = ""
    product_name: str = ""
    quantity: Decimal
    rate: Decimal | None = None
    approved: bool = False


class FrontRhSyncPayload(BaseModel):
    employees: list[dict[str, Any]] = Field(default_factory=list)
    piece_rates: list[dict[str, Any]] = Field(default_factory=list)
    production_entries: list[dict[str, Any]] = Field(default_factory=list)


class PayrollPreviewRequest(BaseModel):
    competence: str
    transport_discount: Decimal = Decimal("0")
    other_additions: Decimal = Decimal("0")
    other_discounts: Decimal = Decimal("0")


class AccessProfileCreate(BaseModel):
    name: str
    description: str = ""
    permissions: list[str] = Field(default_factory=list)
    active: bool = True


class UserCreateExtended(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "user"
    profile_id: str | None = None
    active: bool = True


class SettingPayload(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class FrontClientSyncPayload(BaseModel):
    clients: list[dict[str, Any]] = Field(default_factory=list)


class ClientPriceResolveResponse(BaseModel):
    client_id: str
    product_ref: str
    price: Decimal
    source: str


class UserUpdateExtended(BaseModel):
    full_name: str = ""
    role: str = "user"
    active: bool = True
    profile_id: str | None = None


class UserPasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=200)
