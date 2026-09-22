from __future__ import annotations
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from app.models import Product, ProductVariant
from app.models_extended import StockBalance, StockMovement


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def get_balance(db: Session, product_id: str, location_id: str | None = None, variant_id: str | None = None) -> StockBalance | None:
    conditions = [StockBalance.product_id == product_id]
    conditions.append(StockBalance.location_id.is_(None) if location_id is None else StockBalance.location_id == location_id)
    conditions.append(StockBalance.variant_id.is_(None) if variant_id is None else StockBalance.variant_id == variant_id)
    return db.scalar(select(StockBalance).where(and_(*conditions)))


def ensure_balance(db: Session, product_id: str, location_id: str | None = None, variant_id: str | None = None) -> StockBalance:
    balance = get_balance(db, product_id, location_id, variant_id)
    if balance is None:
        balance = StockBalance(product_id=product_id, location_id=location_id, variant_id=variant_id, quantity=0, reserved_quantity=0)
        db.add(balance); db.flush()
    return balance


def sync_product_totals(db: Session, product_id: str) -> None:
    balances = list(db.scalars(select(StockBalance).where(StockBalance.product_id == product_id)).all())
    if not balances: return
    product = db.get(Product, product_id)
    if product is None: return
    product.stock = sum((dec(x.quantity) for x in balances), Decimal("0"))
    product.reserved_stock = sum((dec(x.reserved_quantity) for x in balances), Decimal("0"))


def move_stock(db: Session, *, product_id: str, quantity: Decimal, movement_type: str, location_id: str | None = None, variant_id: str | None = None, unit_cost: Decimal = Decimal("0"), reference_type: str = "", reference_id: str = "", notes: str = "", user_id: str | None = None, allow_negative: bool = False) -> StockMovement:
    product = db.get(Product, product_id)
    if product is None: raise HTTPException(status_code=404, detail="Produto não encontrado.")
    quantity = dec(quantity)
    if quantity == 0: raise HTTPException(status_code=422, detail="Quantidade não pode ser zero.")
    balance = get_balance(db, product_id, location_id, variant_id)
    if balance is None:
        # Só converte o estoque legado do Product em saldo quando ainda não existe
        # nenhum saldo para o produto. Criar um novo local nunca pode duplicar o total.
        has_any_balance = db.scalar(
            select(StockBalance.id).where(StockBalance.product_id == product_id).limit(1)
        ) is not None
        balance = ensure_balance(db, product_id, location_id, variant_id)
        if not has_any_balance and dec(product.stock) != 0:
            balance.quantity = dec(product.stock)
    new_quantity = dec(balance.quantity) + quantity
    if new_quantity < 0 and not allow_negative:
        raise HTTPException(status_code=409, detail=f"Estoque insuficiente. Disponível: {balance.quantity}.")
    balance.quantity = new_quantity
    movement = StockMovement(product_id=product_id, variant_id=variant_id, location_id=location_id, movement_type=movement_type, quantity=quantity, unit_cost=dec(unit_cost), reference_type=reference_type, reference_id=reference_id, notes=notes, user_id=user_id)
    db.add(movement)
    if unit_cost and quantity > 0: product.cost = dec(unit_cost)
    if variant_id:
        variant = db.get(ProductVariant, variant_id)
        if variant: variant.stock = dec(variant.stock) + quantity
    db.flush(); sync_product_totals(db, product_id)
    return movement


def reserve_stock(db: Session, *, product_id: str, quantity: Decimal, location_id: str | None = None) -> StockBalance:
    quantity = dec(quantity)
    if quantity <= 0: raise HTTPException(status_code=422, detail="Quantidade inválida.")
    balance = get_balance(db, product_id, location_id)
    if balance is None:
        product = db.get(Product, product_id)
        has_any_balance = db.scalar(
            select(StockBalance.id).where(StockBalance.product_id == product_id).limit(1)
        ) is not None
        balance = ensure_balance(db, product_id, location_id)
        if not has_any_balance and product is not None and dec(product.stock) > 0:
            balance.quantity = dec(product.stock)
    available = dec(balance.quantity) - dec(balance.reserved_quantity)
    if available < quantity: raise HTTPException(status_code=409, detail=f"Estoque disponível insuficiente. Disponível: {available}.")
    balance.reserved_quantity = dec(balance.reserved_quantity) + quantity
    db.flush(); sync_product_totals(db, product_id); return balance


def release_reservation(db: Session, *, product_id: str, quantity: Decimal, location_id: str | None = None) -> StockBalance:
    balance = ensure_balance(db, product_id, location_id)
    balance.reserved_quantity = max(Decimal("0"), dec(balance.reserved_quantity) - dec(quantity))
    db.flush(); sync_product_totals(db, product_id); return balance
