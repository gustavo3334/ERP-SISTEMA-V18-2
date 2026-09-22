from __future__ import annotations
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit_service import audit
from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.inventory_service import ensure_balance, move_stock, release_reservation, reserve_stock
from app.models import Product
from app.models_extended import StockBalance, StockMovement
from app.schemas import CurrentUser
from app.schemas_extended import ReservationRequest, StockMovementCreate, StockTransferRequest

router=APIRouter(prefix="/inventory",tags=["Estoque"])

@router.get("/balances",dependencies=[Depends(require_permission("inventory.read"))])
def balances(product_id:str|None=None,db:Session=Depends(get_db)):
    s=select(StockBalance).order_by(StockBalance.updated_at.desc())
    if product_id:s=s.where(StockBalance.product_id==product_id)
    return [{"id":x.id,"product_id":x.product_id,"variant_id":x.variant_id,"location_id":x.location_id,"quantity":x.quantity,"reserved_quantity":x.reserved_quantity,"available_quantity":Decimal(str(x.quantity or 0))-Decimal(str(x.reserved_quantity or 0)),"updated_at":x.updated_at} for x in db.scalars(s).all()]

@router.get("/movements",dependencies=[Depends(require_permission("inventory.read"))])
def movements(product_id:str|None=None,limit:int=200,db:Session=Depends(get_db)):
    s=select(StockMovement).order_by(StockMovement.created_at.desc()).limit(min(limit,1000))
    if product_id:s=s.where(StockMovement.product_id==product_id)
    return [{"id":x.id,"created_at":x.created_at,"product_id":x.product_id,"variant_id":x.variant_id,"location_id":x.location_id,"movement_type":x.movement_type,"quantity":x.quantity,"unit_cost":x.unit_cost,"reference_type":x.reference_type,"reference_id":x.reference_id,"notes":x.notes,"user_id":x.user_id} for x in db.scalars(s).all()]

@router.post("/movements",dependencies=[Depends(require_permission("inventory.write"))])
def create_movement(payload:StockMovementCreate,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    movement=move_stock(db,product_id=payload.product_id,variant_id=payload.variant_id,location_id=payload.location_id,movement_type=payload.movement_type,quantity=payload.quantity,unit_cost=payload.unit_cost,reference_type=payload.reference_type,reference_id=payload.reference_id,notes=payload.notes,user_id=user.id)
    audit(db,module="Estoque",action="MOVIMENTO",entity_type="product",entity_id=payload.product_id,description=f"{payload.movement_type}: {payload.quantity}",user_id=user.id,user_name=user.full_name)
    db.commit();return {"id":movement.id,"status":"ok"}

@router.post("/reserve",dependencies=[Depends(require_permission("inventory.write"))])
def reserve(payload:ReservationRequest,db:Session=Depends(get_db)):
    b=reserve_stock(db,product_id=payload.product_id,quantity=payload.quantity,location_id=payload.location_id);db.commit();return {"quantity":b.quantity,"reserved_quantity":b.reserved_quantity}

@router.post("/release",dependencies=[Depends(require_permission("inventory.write"))])
def release(payload:ReservationRequest,db:Session=Depends(get_db)):
    b=release_reservation(db,product_id=payload.product_id,quantity=payload.quantity,location_id=payload.location_id);db.commit();return {"quantity":b.quantity,"reserved_quantity":b.reserved_quantity}

@router.post("/initialize-from-products",dependencies=[Depends(require_permission("inventory.write"))])
def initialize_from_products(db:Session=Depends(get_db)):
    count=0
    for product in db.scalars(select(Product)).all():
        b=ensure_balance(db,product.id,product.location_id)
        if Decimal(str(b.quantity or 0))==0 and Decimal(str(product.stock or 0))!=0:b.quantity=product.stock;count+=1
    db.commit();return {"initialized":count}


@router.post("/transfer",dependencies=[Depends(require_permission("inventory.write"))])
def transfer(payload:StockTransferRequest,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    """Transfere estoque entre dois locais em uma única transação de banco."""
    if payload.source_location_id == payload.destination_location_id:
        from fastapi import HTTPException
        raise HTTPException(422,"Origem e destino precisam ser diferentes.")
    quantity=Decimal(str(payload.quantity or 0))
    if quantity<=0:
        from fastapi import HTTPException
        raise HTTPException(422,"Quantidade deve ser maior que zero.")

    source=ensure_balance(db,payload.product_id,payload.source_location_id,payload.variant_id)
    available=Decimal(str(source.quantity or 0))-Decimal(str(source.reserved_quantity or 0))
    if available<quantity:
        from fastapi import HTTPException
        raise HTTPException(409,f"Estoque disponível insuficiente na origem. Disponível: {available}.")

    ref=f"TRF-{__import__('uuid').uuid4().hex[:10].upper()}"
    try:
        out_move=move_stock(db,product_id=payload.product_id,variant_id=payload.variant_id,location_id=payload.source_location_id,movement_type="TRANSFERENCIA_SAIDA",quantity=-quantity,reference_type="stock_transfer",reference_id=ref,notes=payload.notes,user_id=user.id)
        in_move=move_stock(db,product_id=payload.product_id,variant_id=payload.variant_id,location_id=payload.destination_location_id,movement_type="TRANSFERENCIA_ENTRADA",quantity=quantity,reference_type="stock_transfer",reference_id=ref,notes=payload.notes,user_id=user.id)
        audit(db,module="Estoque",action="TRANSFERIR",entity_type="product",entity_id=payload.product_id,description=f"{quantity} de {payload.source_location_id} para {payload.destination_location_id}",user_id=user.id,user_name=user.full_name)
        db.commit()
    except Exception:
        db.rollback()
        raise

    source=ensure_balance(db,payload.product_id,payload.source_location_id,payload.variant_id)
    destination=ensure_balance(db,payload.product_id,payload.destination_location_id,payload.variant_id)
    return {
        "status":"ok","reference_id":ref,"product_id":payload.product_id,"quantity":quantity,
        "source":{"location_id":payload.source_location_id,"quantity":source.quantity,"reserved_quantity":source.reserved_quantity},
        "destination":{"location_id":payload.destination_location_id,"quantity":destination.quantity,"reserved_quantity":destination.reserved_quantity},
        "movement_ids":[out_move.id,in_move.id],
    }
