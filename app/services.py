from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import models
from app.schemas import (
    ProductionOrderCreate,
    QuoteItemInput,
    TechnicalItemInput,
    TechnicalSheetCreate,
    TechnicalStageInput,
)


def generate_code(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def money(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def build_technical_sheet(
    db: Session,
    payload: TechnicalSheetCreate,
) -> models.TechnicalSheet:
    sheet = models.TechnicalSheet(
        product_id=payload.product_id,
        code=payload.code,
        category=payload.category,
        version=payload.version,
        notes=payload.notes,
        active=payload.active,
    )
    db.add(sheet)
    db.flush()

    stages_by_order: dict[int, models.TechnicalStage] = {}
    for stage_input in sorted(payload.stages, key=lambda item: item.step_order):
        stage = models.TechnicalStage(
            sheet_id=sheet.id,
            step_order=stage_input.step_order,
            name=stage_input.name,
            sector=stage_input.sector,
            notes=stage_input.notes,
            setup_minutes=stage_input.setup_minutes,
            operation_minutes=stage_input.operation_minutes,
            labor_cost=stage_input.labor_cost,
            machine_cost=stage_input.machine_cost,
            overhead_cost=stage_input.overhead_cost,
            loss_percent=stage_input.loss_percent,
        )
        db.add(stage)
        db.flush()
        stages_by_order[stage.step_order] = stage

        for checklist_input in stage_input.checklist:
            db.add(
                models.TechnicalChecklist(
                    stage_id=stage.id,
                    text=checklist_input.text,
                    required=checklist_input.required,
                )
            )

    for item_input in payload.items:
        stage = (
            stages_by_order.get(item_input.stage_order)
            if item_input.stage_order is not None
            else None
        )
        db.add(
            models.TechnicalSheetItem(
                sheet_id=sheet.id,
                stage_id=stage.id if stage else None,
                component_product_id=item_input.component_product_id,
                item_kind=item_input.item_kind,
                code=item_input.code,
                name=item_input.name,
                quantity=item_input.quantity,
                unit=item_input.unit,
                unit_cost=item_input.unit_cost,
            )
        )

    db.flush()
    recalculate_product_technical_cost(db, sheet)
    return sheet


def replace_technical_sheet_structure(
    db: Session,
    sheet: models.TechnicalSheet,
    stages: list[TechnicalStageInput],
    items: list[TechnicalItemInput],
) -> None:
    for item in list(sheet.items):
        db.delete(item)
    for stage in list(sheet.stages):
        db.delete(stage)
    db.flush()

    stages_by_order: dict[int, models.TechnicalStage] = {}
    for stage_input in sorted(stages, key=lambda item: item.step_order):
        stage = models.TechnicalStage(
            sheet_id=sheet.id,
            step_order=stage_input.step_order,
            name=stage_input.name,
            sector=stage_input.sector,
            notes=stage_input.notes,
            setup_minutes=stage_input.setup_minutes,
            operation_minutes=stage_input.operation_minutes,
            labor_cost=stage_input.labor_cost,
            machine_cost=stage_input.machine_cost,
            overhead_cost=stage_input.overhead_cost,
            loss_percent=stage_input.loss_percent,
        )
        db.add(stage)
        db.flush()
        stages_by_order[stage.step_order] = stage
        for checklist_input in stage_input.checklist:
            db.add(
                models.TechnicalChecklist(
                    stage_id=stage.id,
                    text=checklist_input.text,
                    required=checklist_input.required,
                )
            )

    for item_input in items:
        stage = (
            stages_by_order.get(item_input.stage_order)
            if item_input.stage_order is not None
            else None
        )
        db.add(
            models.TechnicalSheetItem(
                sheet_id=sheet.id,
                stage_id=stage.id if stage else None,
                component_product_id=item_input.component_product_id,
                item_kind=item_input.item_kind,
                code=item_input.code,
                name=item_input.name,
                quantity=item_input.quantity,
                unit=item_input.unit,
                unit_cost=item_input.unit_cost,
            )
        )

    db.flush()
    recalculate_product_technical_cost(db, sheet)


def recalculate_product_technical_cost(
    db: Session,
    sheet: models.TechnicalSheet,
) -> Decimal:
    item_total = sum(
        (money(item.quantity) * money(item.unit_cost) for item in sheet.items),
        Decimal("0"),
    )
    process_total = sum(
        (
            money(stage.labor_cost)
            + money(stage.machine_cost)
            + money(stage.overhead_cost)
            for stage in sheet.stages
        ),
        Decimal("0"),
    )
    total = money(item_total + process_total)
    product = db.get(models.Product, sheet.product_id)
    if product:
        product.technical_cost = total
    return total


def load_technical_sheet(db: Session, sheet_id: str) -> models.TechnicalSheet | None:
    return db.scalar(
        select(models.TechnicalSheet)
        .where(models.TechnicalSheet.id == sheet_id)
        .options(
            selectinload(models.TechnicalSheet.product),
            selectinload(models.TechnicalSheet.items),
            selectinload(models.TechnicalSheet.stages).selectinload(
                models.TechnicalStage.checklist
            ),
        )
    )


PRODUCTION_MODES = {
    "PRODUZIR_DO_ZERO",
    "BAU_BLINDADO",
    "RETIRAR_ESTOQUE_VAZADO",
}


def production_mode_label(mode: str) -> str:
    return {
        "PRODUZIR_DO_ZERO": "Produzir do zero",
        "BAU_BLINDADO": "Produzir baú blindado",
        "RETIRAR_ESTOQUE_VAZADO": "Retirar do estoque de vazado",
    }.get(mode, mode)


def _add_blindagem_stage(db: Session, order: models.ProductionOrder, step_order: int) -> None:
    stage = models.ProductionOrderStage(
        order_id=order.id,
        template_stage_id=None,
        step_order=step_order,
        name="BLINDAGEM",
        sector="Blindagem",
        responsible="",
        status="Pendente",
        planned_material_cost=Decimal("0"),
        planned_labor_cost=Decimal("0"),
        planned_machine_cost=Decimal("0"),
        planned_overhead_cost=Decimal("0"),
        notes="Etapa específica do modo baú blindado. Materiais e custos podem ser apontados na OP.",
    )
    db.add(stage)
    db.flush()
    db.add_all([
        models.ProductionOrderChecklist(
            stage_id=stage.id,
            text="Conferir blindagem antes de liberar a próxima etapa",
            done=False,
        ),
        models.ProductionOrderChecklist(
            stage_id=stage.id,
            text="Registrar inspeção da blindagem",
            done=False,
        ),
    ])


def _add_vazado_withdrawal_stage(
    db: Session,
    order: models.ProductionOrder,
    source: models.Product,
    quantity: Decimal,
) -> models.ProductionOrderStage:
    total_cost = money(source.cost) * quantity
    stage = models.ProductionOrderStage(
        order_id=order.id,
        template_stage_id=None,
        step_order=1,
        name="RETIRADA DO ESTOQUE DE VAZADO",
        sector="Estoque",
        responsible="",
        status="Pendente",
        planned_material_cost=money(total_cost),
        planned_labor_cost=Decimal("0"),
        planned_machine_cost=Decimal("0"),
        planned_overhead_cost=Decimal("0"),
        notes=f"Retirar {quantity} {source.unit or 'UN'} de {source.code} · {source.name}.",
    )
    db.add(stage)
    db.flush()
    db.add(
        models.ProductionOrderStageItem(
            stage_id=stage.id,
            item_kind="Vazado em estoque",
            code=source.code,
            name=source.name,
            quantity=quantity,
            unit=source.unit or "UN",
            unit_cost=source.cost,
            total_cost=money(total_cost),
            consumed=True,
        )
    )
    db.add(
        models.ProductionOrderChecklist(
            stage_id=stage.id,
            text="Conferir quantidade e condição do vazado retirado do estoque",
            done=False,
        )
    )
    return stage


def create_production_order(
    db: Session,
    payload: ProductionOrderCreate,
) -> models.ProductionOrder:
    mode = (payload.production_mode or "PRODUZIR_DO_ZERO").strip().upper()
    if mode not in PRODUCTION_MODES:
        raise ValueError("Forma de produção inválida.")

    product = db.get(models.Product, payload.product_id) if payload.product_id else None
    sheet = (
        load_technical_sheet(db, payload.technical_sheet_id)
        if payload.technical_sheet_id
        else None
    )

    product_name = payload.product_name or (product.name if product else "")
    if not product_name:
        raise ValueError("Informe o produto da ordem.")

    quantity = Decimal(str(payload.quantity or 1))
    if quantity <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    source_product = None
    source_cost = Decimal("0")
    if mode == "RETIRAR_ESTOQUE_VAZADO":
        if not payload.source_stock_product_id:
            raise ValueError("Selecione o baú vazado que será retirado do estoque.")
        source_product = db.get(models.Product, payload.source_stock_product_id)
        if source_product is None:
            raise ValueError("O item de estoque selecionado não foi encontrado.")
        available = Decimal(str(source_product.stock or 0))
        if available < quantity:
            raise ValueError(
                f"Estoque insuficiente. Disponível: {available} {source_product.unit or 'UN'}."
            )
        from app.inventory_service import move_stock
        move_stock(
            db,
            product_id=source_product.id,
            quantity=-quantity,
            movement_type="CONSUMO_VAZADO_PRODUCAO",
            location_id=source_product.location_id,
            unit_cost=source_product.cost,
            reference_type="production_order_draft",
            reference_id="",
            notes="Retirada de vazado para nova ordem de produção.",
        )
        source_cost = money(source_product.cost) * quantity

    order = models.ProductionOrder(
        code=generate_code("OP"),
        order_ref=payload.order_ref,
        product_id=payload.product_id,
        technical_sheet_id=payload.technical_sheet_id,
        production_mode=mode,
        source_stock_product_id=(source_product.id if source_product else None),
        source_stock_quantity=(quantity if source_product else Decimal("0")),
        source_stock_cost=money(source_cost),
        product_name=product_name,
        quantity=quantity,
        responsible=payload.responsible,
        start_date=payload.start_date or date.today(),
        forecast_date=payload.forecast_date,
        workflow_stage=payload.workflow_stage,
        progress=Decimal("0"),
        status="Pendente",
        priority=payload.priority,
        notes=payload.notes,
    )
    db.add(order)
    db.flush()

    material_total = Decimal("0")
    process_total = Decimal("0")
    order_step_offset = 0

    if source_product is not None:
        _add_vazado_withdrawal_stage(db, order, source_product, quantity)
        material_total += source_cost
        order_step_offset = 1

    if sheet:
        templates = list(sheet.stages)
        for template_stage in templates:
            stage_items = [
                item for item in sheet.items if item.stage_id == template_stage.id
            ]
            planned_material = sum(
                (
                    money(item.quantity)
                    * quantity
                    * money(item.unit_cost)
                    for item in stage_items
                ),
                Decimal("0"),
            )
            planned_process = (
                money(template_stage.labor_cost)
                + money(template_stage.machine_cost)
                + money(template_stage.overhead_cost)
            ) * quantity

            stage_order = template_stage.step_order + order_step_offset
            order_stage = models.ProductionOrderStage(
                order_id=order.id,
                template_stage_id=template_stage.id,
                step_order=stage_order,
                name=template_stage.name,
                sector=template_stage.sector,
                responsible="",
                status="Pendente",
                planned_material_cost=planned_material,
                planned_labor_cost=money(template_stage.labor_cost) * quantity,
                planned_machine_cost=money(template_stage.machine_cost) * quantity,
                planned_overhead_cost=money(template_stage.overhead_cost) * quantity,
                notes=template_stage.notes,
            )
            db.add(order_stage)
            db.flush()

            for item in stage_items:
                item_quantity = money(item.quantity) * quantity
                total_cost = item_quantity * money(item.unit_cost)
                db.add(
                    models.ProductionOrderStageItem(
                        stage_id=order_stage.id,
                        item_kind=item.item_kind,
                        code=item.code,
                        name=item.name,
                        quantity=item_quantity,
                        unit=item.unit,
                        unit_cost=item.unit_cost,
                        total_cost=total_cost,
                        consumed=False,
                    )
                )

            for checklist in template_stage.checklist:
                db.add(
                    models.ProductionOrderChecklist(
                        stage_id=order_stage.id,
                        text=checklist.text,
                        done=False,
                    )
                )

            material_total += planned_material
            process_total += planned_process

    if mode == "BAU_BLINDADO":
        max_step = db.scalar(
            select(func.coalesce(func.max(models.ProductionOrderStage.step_order), 0))
            .where(models.ProductionOrderStage.order_id == order.id)
        ) or 0
        _add_blindagem_stage(db, order, int(max_step) + 1)

    order.planned_material_cost = money(material_total)
    order.planned_process_cost = money(process_total)

    db.flush()
    return order


def load_production_order(
    db: Session,
    order_id: str,
) -> models.ProductionOrder | None:
    return db.scalar(
        select(models.ProductionOrder)
        .where(models.ProductionOrder.id == order_id)
        .options(
            selectinload(models.ProductionOrder.stages).selectinload(
                models.ProductionOrderStage.items
            ),
            selectinload(models.ProductionOrder.stages).selectinload(
                models.ProductionOrderStage.checklist
            ),
        )
    )


def recalculate_order(db: Session, order: models.ProductionOrder) -> None:
    stages = list(order.stages)
    if stages:
        completed = sum(1 for stage in stages if stage.status == "Concluída")
        order.progress = Decimal(str(round((completed / len(stages)) * 100, 2)))

    actual_total = Decimal("0")
    for stage in stages:
        actual_total += (
            money(stage.actual_material_cost)
            + money(stage.actual_labor_cost)
            + money(stage.actual_machine_cost)
            + money(stage.actual_overhead_cost)
            + money(stage.loss_cost)
        )
    order.actual_cost = money(actual_total)

    progress = float(order.progress or 0)
    if progress >= 100:
        order.workflow_stage = "Pronto"
        order.status = "Concluída"
    elif progress >= 70:
        order.workflow_stage = "Acabamento"
        order.status = "Em produção"
    elif progress > 0 or any(stage.status == "Em andamento" for stage in stages):
        order.workflow_stage = "Produção"
        order.status = "Em produção"
    else:
        order.workflow_stage = "Novo pedido"
        order.status = "Pendente"


def calculate_quote_item(item: QuoteItemInput) -> Decimal:
    gross = money(item.quantity) * money(item.unit_price)
    discount = money(item.discount) / Decimal("100")
    return money(gross * (Decimal("1") - discount))
