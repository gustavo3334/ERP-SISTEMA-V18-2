from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import (
    Product,
    ProductionOrder,
    ProductionOrderChecklist,
    ProductionOrderStage,
    ProductionOrderStageItem,
)
from app.schemas import (
    ProductionOrderCreate,
    ProductionOrderRead,
    ProductionOrderUpdate,
    ProductionStagePatch,
)
from app.inventory_service import move_stock
from app.services import (
    create_production_order,
    load_production_order,
    recalculate_order,
)


router = APIRouter(
    prefix="/production-orders",
    tags=["Produção e PCP"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ProductionOrderRead], dependencies=[Depends(require_permission("pcp.read"))])
def list_orders(db: Session = Depends(get_db)):
    statement = (
        select(ProductionOrder)
        .options(
            selectinload(ProductionOrder.stages).selectinload(
                ProductionOrderStage.items
            ),
            selectinload(ProductionOrder.stages).selectinload(
                ProductionOrderStage.checklist
            ),
        )
        .order_by(ProductionOrder.created_at.desc())
    )
    return list(db.scalars(statement).unique().all())


@router.get("/options/production-modes", dependencies=[Depends(require_permission("pcp.read"))])
def production_modes():
    return [
        {"value": "PRODUZIR_DO_ZERO", "label": "Produzir do zero"},
        {"value": "BAU_BLINDADO", "label": "Produzir baú blindado"},
        {"value": "RETIRAR_ESTOQUE_VAZADO", "label": "Retirar do estoque de vazado"},
    ]


@router.get("/options/vazado-stock", dependencies=[Depends(require_permission("pcp.read"))])
def vazado_stock(db: Session = Depends(get_db)):
    statement = (
        select(Product)
        .where(Product.active.is_(True), Product.stock > 0)
        .order_by(Product.name.asc())
    )
    products = list(db.scalars(statement).all())
    filtered = [
        item for item in products
        if item.item_type == "Pré-fabricado"
        or "VAZADO" in (item.name or "").upper()
        or "BAU" in (item.name or "").upper()
    ]
    return [
        {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "stock": item.stock,
            "unit": item.unit,
            "cost": item.cost,
            "location_id": item.location_id,
        }
        for item in filtered
    ]


@router.get("/{order_id}", response_model=ProductionOrderRead, dependencies=[Depends(require_permission("pcp.read"))])
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = load_production_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")
    return order


@router.post(
    "",
    response_model=ProductionOrderRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("pcp.write"))],
)
def create_order(payload: ProductionOrderCreate, db: Session = Depends(get_db)):
    try:
        order = create_production_order(db, payload)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return load_production_order(db, order.id)


@router.put("/{order_id}", response_model=ProductionOrderRead, dependencies=[Depends(require_permission("pcp.write"))])
def update_order(
    order_id: str,
    payload: ProductionOrderUpdate,
    db: Session = Depends(get_db),
):
    order = load_production_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    db.commit()
    return load_production_order(db, order.id)


@router.patch("/{order_id}/workflow-stage", response_model=ProductionOrderRead, dependencies=[Depends(require_permission("pcp.write"))])
def change_workflow_stage(
    order_id: str,
    stage: str,
    db: Session = Depends(get_db),
):
    allowed = {
        "Novo pedido",
        "Separação",
        "Produção",
        "Acabamento",
        "Pronto",
        "Entrega",
    }
    if stage not in allowed:
        raise HTTPException(status_code=422, detail="Etapa do Kanban inválida.")

    order = load_production_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")
    order.workflow_stage = stage
    db.commit()
    return load_production_order(db, order.id)


@router.patch(
    "/{order_id}/stages/{stage_id}",
    response_model=ProductionOrderRead,
    dependencies=[Depends(require_permission("pcp.write"))],
)
def update_order_stage(
    order_id: str,
    stage_id: str,
    payload: ProductionStagePatch,
    db: Session = Depends(get_db),
):
    order = load_production_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")

    stage = next((item for item in order.stages if item.id == stage_id), None)
    if stage is None:
        raise HTTPException(status_code=404, detail="Etapa não encontrada.")

    data = payload.model_dump(
        exclude_unset=True,
        exclude={"consumed_item_ids", "completed_checklist_ids"},
    )
    for key, value in data.items():
        setattr(stage, key, value)

    if payload.consumed_item_ids is not None:
        consumed = set(payload.consumed_item_ids)
        for item in stage.items:
            next_value = item.id in consumed
            if next_value != item.consumed:
                product = db.scalar(select(Product).where(Product.code == item.code))
                if product is not None:
                    move_stock(
                        db, product_id=product.id,
                        quantity=(-item.quantity if next_value else item.quantity),
                        movement_type=("CONSUMO_PRODUCAO" if next_value else "DEVOLUCAO_PRODUCAO"),
                        location_id=product.location_id, unit_cost=item.unit_cost,
                        reference_type="production_order", reference_id=order.id,
                        notes=f"Etapa {stage.name}",
                    )
            item.consumed = next_value

    if payload.completed_checklist_ids is not None:
        completed = set(payload.completed_checklist_ids)
        for item in stage.checklist:
            item.done = item.id in completed

    recalculate_order(db, order)
    db.commit()
    return load_production_order(db, order.id)


@router.post("/{order_id}/advance", response_model=ProductionOrderRead, dependencies=[Depends(require_permission("pcp.write"))])
def advance_stage(order_id: str, db: Session = Depends(get_db)):
    order = load_production_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")

    active = next(
        (stage for stage in order.stages if stage.status == "Em andamento"),
        None,
    )
    if active:
        active.status = "Concluída"
        next_stage = next(
            (
                stage
                for stage in order.stages
                if stage.step_order > active.step_order
                and stage.status == "Pendente"
            ),
            None,
        )
        if next_stage:
            next_stage.status = "Em andamento"
    else:
        pending = next(
            (stage for stage in order.stages if stage.status == "Pendente"),
            None,
        )
        if pending:
            pending.status = "Em andamento"

    recalculate_order(db, order)
    db.commit()
    return load_production_order(db, order.id)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("pcp.write"))])
def delete_order(order_id: str, db: Session = Depends(get_db)):
    order = db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")
    if (
        order.production_mode == "RETIRAR_ESTOQUE_VAZADO"
        and order.source_stock_product_id
        and order.source_stock_quantity
    ):
        source = db.get(Product, order.source_stock_product_id)
        if source is not None:
            move_stock(
                db, product_id=source.id, quantity=order.source_stock_quantity,
                movement_type="DEVOLUCAO_CANCELAMENTO_OP", location_id=source.location_id,
                unit_cost=source.cost, reference_type="production_order", reference_id=order.id,
                notes=f"Cancelamento da {order.code}",
            )

    db.delete(order)
    db.commit()
    return None


@router.post("/{order_id}/complete", response_model=ProductionOrderRead, dependencies=[Depends(require_permission("pcp.write"))])
def complete_order(order_id: str, db: Session = Depends(get_db)):
    order = load_production_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")
    if any(stage.status != "Concluída" for stage in order.stages):
        raise HTTPException(status_code=409, detail="Todas as etapas precisam estar concluídas antes de finalizar a OP.")
    if order.product_id:
        product = db.get(Product, order.product_id)
        if product:
            move_stock(db, product_id=product.id, quantity=order.quantity, movement_type="ENTRADA_PRODUCAO", location_id=product.location_id, unit_cost=order.actual_cost or product.technical_cost or product.cost, reference_type="production_order", reference_id=order.id, notes=f"Conclusão da {order.code}")
    order.progress = 100; order.workflow_stage = "Pronto"; order.status = "Concluída"
    db.commit()
    return load_production_order(db, order.id)
