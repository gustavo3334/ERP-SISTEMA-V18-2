from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Timestamped(ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


class BranchCreate(BaseModel):
    code: str
    name: str
    active: bool = True


class BranchUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    active: bool | None = None


class BranchRead(BranchCreate, Timestamped):
    pass


class ClientCreate(BaseModel):
    name: str
    legacy_id: str | None = None
    document: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    status: str = "Ativo"
    credit_limit: Decimal = Decimal("0")
    preferred_payment: str = ""
    payment_methods_json: list[Any] | None = Field(default_factory=list)
    purchase_history: str = ""
    front_payload_json: dict[str, Any] | None = Field(default_factory=dict)
    notes: str = ""
    active: bool = True


class ClientUpdate(BaseModel):
    name: str | None = None
    legacy_id: str | None = None
    document: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    status: str | None = None
    credit_limit: Decimal | None = None
    preferred_payment: str | None = None
    payment_methods_json: list[Any] | None = None
    purchase_history: str | None = None
    front_payload_json: dict[str, Any] | None = None
    notes: str | None = None
    active: bool | None = None


class ClientRead(ClientCreate, Timestamped):
    pass


class SupplierCreate(BaseModel):
    legal_name: str
    trade_name: str = ""
    document: str = ""
    email: str = ""
    phone: str = ""
    notes: str = ""
    active: bool = True


class SupplierUpdate(BaseModel):
    legal_name: str | None = None
    trade_name: str | None = None
    document: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    active: bool | None = None


class SupplierRead(SupplierCreate, Timestamped):
    pass


class CategoryCreate(BaseModel):
    name: str
    item_type: str = "Produto acabado"
    description: str = ""
    active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = None
    item_type: str | None = None
    description: str | None = None
    active: bool | None = None


class CategoryRead(CategoryCreate, Timestamped):
    pass


class StockLocationCreate(BaseModel):
    name: str
    warehouse: str = ""
    aisle: str = ""
    rack: str = ""
    shelf: str = ""
    address_code: str
    description: str = ""
    active: bool = True


class StockLocationUpdate(BaseModel):
    name: str | None = None
    warehouse: str | None = None
    aisle: str | None = None
    rack: str | None = None
    shelf: str | None = None
    address_code: str | None = None
    description: str | None = None
    active: bool | None = None


class StockLocationRead(StockLocationCreate, Timestamped):
    pass


class ProductCreate(BaseModel):
    code: str
    name: str
    description: str = ""
    item_type: str = "Produto acabado"
    category_id: str | None = None
    supplier_id: str | None = None
    location_id: str | None = None
    color: str = ""
    size: str = ""
    unit: str = "UN"
    cost: Decimal = Decimal("0")
    technical_cost: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    stock: Decimal = Decimal("0")
    reserved_stock: Decimal = Decimal("0")
    min_stock: Decimal = Decimal("0")
    base_stock: Decimal = Decimal("0")
    manufacturing_enabled: bool = False
    active: bool = True


class ProductUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    item_type: str | None = None
    category_id: str | None = None
    supplier_id: str | None = None
    location_id: str | None = None
    color: str | None = None
    size: str | None = None
    unit: str | None = None
    cost: Decimal | None = None
    technical_cost: Decimal | None = None
    price: Decimal | None = None
    stock: Decimal | None = None
    reserved_stock: Decimal | None = None
    min_stock: Decimal | None = None
    base_stock: Decimal | None = None
    manufacturing_enabled: bool | None = None
    active: bool | None = None


class ProductRead(ProductCreate, Timestamped):
    pass


class ProductVariantCreate(BaseModel):
    product_id: str
    sku: str
    barcode: str = ""
    color: str = ""
    size: str = ""
    supplier_id: str | None = None
    location_id: str | None = None
    stock: Decimal = Decimal("0")
    reserved_stock: Decimal = Decimal("0")
    min_stock: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    price: Decimal = Decimal("0")


class ProductVariantUpdate(BaseModel):
    product_id: str | None = None
    sku: str | None = None
    barcode: str | None = None
    color: str | None = None
    size: str | None = None
    supplier_id: str | None = None
    location_id: str | None = None
    stock: Decimal | None = None
    reserved_stock: Decimal | None = None
    min_stock: Decimal | None = None
    cost: Decimal | None = None
    price: Decimal | None = None


class ProductVariantRead(ProductVariantCreate, Timestamped):
    pass


class TechnicalChecklistInput(BaseModel):
    text: str
    required: bool = True


class TechnicalStageInput(BaseModel):
    step_order: int
    name: str
    sector: str = ""
    notes: str = ""
    setup_minutes: int = 0
    operation_minutes: int = 0
    labor_cost: Decimal = Decimal("0")
    machine_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    loss_percent: Decimal = Decimal("0")
    checklist: list[TechnicalChecklistInput] = Field(default_factory=list)


class TechnicalItemInput(BaseModel):
    stage_order: int | None = None
    component_product_id: str | None = None
    item_kind: str = "Matéria-prima"
    code: str
    name: str
    quantity: Decimal
    unit: str = "UN"
    unit_cost: Decimal = Decimal("0")


class TechnicalSheetCreate(BaseModel):
    product_id: str
    code: str
    category: str = ""
    version: int = 1
    notes: str = ""
    active: bool = True
    stages: list[TechnicalStageInput] = Field(default_factory=list)
    items: list[TechnicalItemInput] = Field(default_factory=list)


class TechnicalSheetUpdate(BaseModel):
    code: str | None = None
    category: str | None = None
    version: int | None = None
    notes: str | None = None
    active: bool | None = None
    stages: list[TechnicalStageInput] | None = None
    items: list[TechnicalItemInput] | None = None


class TechnicalChecklistRead(TechnicalChecklistInput, Timestamped):
    stage_id: str


class TechnicalStageRead(ORMModel):
    id: str
    sheet_id: str
    step_order: int
    name: str
    sector: str
    notes: str
    setup_minutes: int
    operation_minutes: int
    labor_cost: Decimal
    machine_cost: Decimal
    overhead_cost: Decimal
    loss_percent: Decimal
    checklist: list[TechnicalChecklistRead]
    created_at: datetime
    updated_at: datetime


class TechnicalItemRead(ORMModel):
    id: str
    sheet_id: str
    stage_id: str | None
    component_product_id: str | None
    item_kind: str
    code: str
    name: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    created_at: datetime
    updated_at: datetime


class TechnicalSheetRead(ORMModel):
    id: str
    product_id: str
    code: str
    category: str
    version: int
    notes: str
    active: bool
    stages: list[TechnicalStageRead]
    items: list[TechnicalItemRead]
    created_at: datetime
    updated_at: datetime


class ProductionOrderCreate(BaseModel):
    order_ref: str = ""
    product_id: str | None = None
    technical_sheet_id: str | None = None
    production_mode: str = "PRODUZIR_DO_ZERO"
    source_stock_product_id: str | None = None
    product_name: str = ""
    quantity: Decimal = Decimal("1")
    responsible: str = ""
    start_date: date | None = None
    forecast_date: date | None = None
    workflow_stage: str = "Novo pedido"
    priority: str = "Normal"
    notes: str = ""


class ProductionOrderUpdate(BaseModel):
    order_ref: str | None = None
    product_id: str | None = None
    technical_sheet_id: str | None = None
    production_mode: str | None = None
    source_stock_product_id: str | None = None
    product_name: str | None = None
    quantity: Decimal | None = None
    responsible: str | None = None
    start_date: date | None = None
    forecast_date: date | None = None
    workflow_stage: str | None = None
    progress: Decimal | None = None
    status: str | None = None
    priority: str | None = None
    notes: str | None = None


class ProductionStagePatch(BaseModel):
    status: str | None = None
    responsible: str | None = None
    actual_material_cost: Decimal | None = None
    actual_labor_cost: Decimal | None = None
    actual_machine_cost: Decimal | None = None
    actual_overhead_cost: Decimal | None = None
    loss_cost: Decimal | None = None
    notes: str | None = None
    consumed_item_ids: list[str] | None = None
    completed_checklist_ids: list[str] | None = None


class ProductionStageItemRead(ORMModel):
    id: str
    item_kind: str
    code: str
    name: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    total_cost: Decimal
    consumed: bool


class ProductionChecklistRead(ORMModel):
    id: str
    text: str
    done: bool


class ProductionStageRead(ORMModel):
    id: str
    step_order: int
    name: str
    sector: str
    responsible: str
    status: str
    planned_material_cost: Decimal
    planned_labor_cost: Decimal
    planned_machine_cost: Decimal
    planned_overhead_cost: Decimal
    actual_material_cost: Decimal
    actual_labor_cost: Decimal
    actual_machine_cost: Decimal
    actual_overhead_cost: Decimal
    loss_cost: Decimal
    notes: str
    items: list[ProductionStageItemRead]
    checklist: list[ProductionChecklistRead]


class ProductionOrderRead(ORMModel):
    id: str
    code: str
    order_ref: str
    product_id: str | None
    technical_sheet_id: str | None
    production_mode: str
    source_stock_product_id: str | None
    source_stock_quantity: Decimal
    source_stock_cost: Decimal
    product_name: str
    quantity: Decimal
    responsible: str
    start_date: date | None
    forecast_date: date | None
    workflow_stage: str
    progress: Decimal
    status: str
    priority: str
    planned_material_cost: Decimal
    planned_process_cost: Decimal
    actual_cost: Decimal
    notes: str
    stages: list[ProductionStageRead]
    created_at: datetime
    updated_at: datetime


class DeliveryCreate(BaseModel):
    client_id: str | None = None
    order_ref: str = ""
    recipient_name: str
    address: str
    scheduled_date: date
    scheduled_time: time | None = None
    route_name: str = ""
    driver_name: str = ""
    status: str = "Agendada"
    occurrence: str = ""
    notes: str = ""


class DeliveryUpdate(BaseModel):
    client_id: str | None = None
    order_ref: str | None = None
    recipient_name: str | None = None
    address: str | None = None
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    route_name: str | None = None
    driver_name: str | None = None
    status: str | None = None
    occurrence: str | None = None
    notes: str | None = None


class DeliveryRead(DeliveryCreate, Timestamped):
    code: str


class QuoteItemInput(BaseModel):
    product_id: str | None = None
    product_name: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")


class QuoteCreate(BaseModel):
    client_id: str | None = None
    client_name: str = ""
    valid_until: date | None = None
    probability: Decimal = Decimal("0")
    payment_method: str = ""
    status: str = "Rascunho"
    notes: str = ""
    items: list[QuoteItemInput] = Field(default_factory=list)


class QuoteUpdate(BaseModel):
    client_id: str | None = None
    client_name: str | None = None
    valid_until: date | None = None
    probability: Decimal | None = None
    payment_method: str | None = None
    status: str | None = None
    notes: str | None = None
    items: list[QuoteItemInput] | None = None


class QuoteItemRead(ORMModel):
    id: str
    product_id: str | None
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    total: Decimal


class QuoteRead(ORMModel):
    id: str
    code: str
    client_id: str | None
    client_name: str
    valid_until: date | None
    probability: Decimal
    payment_method: str
    status: str
    notes: str
    total: Decimal
    items: list[QuoteItemRead]
    created_at: datetime
    updated_at: datetime


class FinancialEntryCreate(BaseModel):
    kind: str = "Receita"
    description: str
    category: str = ""
    due_date: date | None = None
    amount: Decimal = Decimal("0")
    status: str = "A vencer"
    notes: str = ""


class FinancialEntryUpdate(BaseModel):
    kind: str | None = None
    description: str | None = None
    category: str | None = None
    due_date: date | None = None
    amount: Decimal | None = None
    status: str | None = None
    notes: str | None = None


class FinancialEntryRead(FinancialEntryCreate, Timestamped):
    pass


class LoginRequest(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str = ""


class CurrentUser(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    active: bool = True


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: CurrentUser
    permissions: list[str] = Field(default_factory=list)


class FrontStatePayload(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    # Revisão que o navegador leu antes de salvar. Evita que uma aba/computador
    # com estado antigo sobrescreva silenciosamente dados mais novos do servidor.
    base_revision: int | None = None


class FrontStateRead(BaseModel):
    state_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    revision: int = 0
    updated_at: datetime | None = None


class FrontStateRevisionRead(BaseModel):
    state_key: str
    revision: int
    payload: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    created_at: datetime | None = None


class DashboardSummary(BaseModel):
    clients: int
    suppliers: int
    products: int
    technical_sheets: int
    production_orders: int
    active_production_orders: int
    deliveries: int
    deliveries_today: int
    quotes: int
    receivables: Decimal
    payables: Decimal


class RoutePoint(BaseModel):
    input_address: str
    formatted_address: str
    latitude: float
    longitude: float


class RouteCalculateRequest(BaseModel):
    origin_address: str = Field(min_length=5)
    destination_address: str = Field(min_length=5)
    travel_mode: str = "DRIVE"


class RouteCalculateResponse(BaseModel):
    provider: str
    travel_mode: str
    origin: RoutePoint
    destination: RoutePoint
    distance_meters: int
    distance_km: float
    round_trip_distance_km: float
    duration_seconds: int
    duration_minutes: int
    round_trip_duration_minutes: int
    coordinates: list[list[float]] = Field(default_factory=list)
    map_attribution: str = ""
    warning: str = ""
