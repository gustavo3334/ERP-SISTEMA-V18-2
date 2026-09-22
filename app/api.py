from __future__ import annotations

from fastapi import APIRouter

from app import models, schemas
from app.crud import build_crud_router
from app.routers import api_root, auth, dashboard, front_state, production, quotes, technical_sheets
from app.routers import access_control, clients, employees, files, inventory, purchasing, sales, system_admin, routes


api_router = APIRouter()

api_router.include_router(api_root.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(front_state.router)
api_router.include_router(technical_sheets.router)
api_router.include_router(production.router)
api_router.include_router(quotes.router)
api_router.include_router(inventory.router)
api_router.include_router(purchasing.router)
api_router.include_router(sales.router)
api_router.include_router(employees.router)
api_router.include_router(clients.router)
api_router.include_router(files.router)
api_router.include_router(access_control.router)
api_router.include_router(system_admin.router)
api_router.include_router(routes.router)

api_router.include_router(
    build_crud_router(
        model=models.Branch,
        create_schema=schemas.BranchCreate,
        update_schema=schemas.BranchUpdate,
        read_schema=schemas.BranchRead,
        prefix="branches",
        tag="Unidades",
        search_fields=("code", "name"),
        read_permission="dashboard.read",
        write_permission="settings.write",
    )
)

api_router.include_router(
    build_crud_router(
        model=models.Client,
        create_schema=schemas.ClientCreate,
        update_schema=schemas.ClientUpdate,
        read_schema=schemas.ClientRead,
        prefix="clients",
        tag="Clientes",
        search_fields=("name", "document", "email", "phone"),
        read_permission="clients.read",
        write_permission="clients.write",
    )
)

api_router.include_router(
    build_crud_router(
        model=models.Supplier,
        create_schema=schemas.SupplierCreate,
        update_schema=schemas.SupplierUpdate,
        read_schema=schemas.SupplierRead,
        prefix="suppliers",
        tag="Fornecedores",
        search_fields=("legal_name", "trade_name", "document", "email"),
        read_permission="purchasing.read",
        write_permission="purchasing.write",
    )
)

api_router.include_router(
    build_crud_router(
        model=models.Category,
        create_schema=schemas.CategoryCreate,
        update_schema=schemas.CategoryUpdate,
        read_schema=schemas.CategoryRead,
        prefix="categories",
        tag="Categorias",
        search_fields=("name", "item_type"),
        read_permission="products.read",
        write_permission="products.write",
    )
)

api_router.include_router(
    build_crud_router(
        model=models.StockLocation,
        create_schema=schemas.StockLocationCreate,
        update_schema=schemas.StockLocationUpdate,
        read_schema=schemas.StockLocationRead,
        prefix="stock-locations",
        tag="Locais de estoque",
        search_fields=("name", "warehouse", "address_code"),
        read_permission="inventory.read",
        write_permission="inventory.write",
    )
)

api_router.include_router(
    build_crud_router(
        model=models.Product,
        create_schema=schemas.ProductCreate,
        update_schema=schemas.ProductUpdate,
        read_schema=schemas.ProductRead,
        prefix="products",
        tag="Produtos e materiais",
        search_fields=("code", "name", "item_type", "color", "size"),
        read_permission="products.read",
        write_permission="products.write",
    )
)

api_router.include_router(
    build_crud_router(
        model=models.ProductVariant,
        create_schema=schemas.ProductVariantCreate,
        update_schema=schemas.ProductVariantUpdate,
        read_schema=schemas.ProductVariantRead,
        prefix="product-variants",
        tag="Variações de produto",
        search_fields=("sku", "barcode", "color", "size"),
        read_permission="products.read",
        write_permission="products.write",
    )
)

api_router.include_router(
    build_crud_router(
        model=models.Delivery,
        create_schema=schemas.DeliveryCreate,
        update_schema=schemas.DeliveryUpdate,
        read_schema=schemas.DeliveryRead,
        prefix="deliveries",
        tag="Entregas e rotas",
        search_fields=("code", "recipient_name", "order_ref", "route_name", "status"),
        read_permission="deliveries.read",
        write_permission="deliveries.write",
    )
)

api_router.include_router(
    build_crud_router(
        model=models.FinancialEntry,
        create_schema=schemas.FinancialEntryCreate,
        update_schema=schemas.FinancialEntryUpdate,
        read_schema=schemas.FinancialEntryRead,
        prefix="financial-entries",
        tag="Financeiro",
        search_fields=("kind", "description", "category", "status"),
        read_permission="finance.read",
        write_permission="finance.write",
    )
)
