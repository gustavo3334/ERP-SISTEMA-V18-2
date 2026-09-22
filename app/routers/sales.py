from __future__ import annotations
from datetime import date
from decimal import Decimal
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import or_,select
from sqlalchemy.orm import Session,selectinload
from app.audit_service import audit
from app.database import get_db
from app.dependencies import get_current_user,require_permission
from app.inventory_service import move_stock,release_reservation,reserve_stock
from app.models import ClientProductPrice,Delivery,FinancialEntry,Product,ProductionOrder,TechnicalSheet
from app.models_extended import SalesOrder,SalesOrderItem
from app.schemas import CurrentUser,ProductionOrderCreate
from app.schemas_extended import SalesConfirmRequest,SalesOrderCreate
from app.services import create_production_order

router=APIRouter(prefix="/sales-orders",tags=["Vendas"])
def new_code():return f"PED-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
def load(db,id):return db.scalar(select(SalesOrder).where(SalesOrder.id==id).options(selectinload(SalesOrder.items)))
def out(o):return {"id":o.id,"code":o.code,"client_id":o.client_id,"client_name":o.client_name,"issue_date":o.issue_date,"status":o.status,"payment_method":o.payment_method,"delivery_address":o.delivery_address,"notes":o.notes,"subtotal":o.subtotal,"discount":o.discount,"freight":o.freight,"total":o.total,"items":[{"id":i.id,"product_id":i.product_id,"description":i.description,"quantity":i.quantity,"unit_price":i.unit_price,"discount_percent":i.discount_percent,"total":i.total,"production_order_id":i.production_order_id} for i in o.items]}

@router.get("",dependencies=[Depends(require_permission("sales.read"))])
def list_orders(db:Session=Depends(get_db)):
    return [out(x) for x in db.scalars(select(SalesOrder).options(selectinload(SalesOrder.items)).order_by(SalesOrder.created_at.desc())).unique().all()]

@router.post("",status_code=201,dependencies=[Depends(require_permission("sales.write"))])
def create(payload:SalesOrderCreate,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    o=SalesOrder(code=new_code(),client_id=payload.client_id,client_name=payload.client_name,payment_method=payload.payment_method,delivery_address=payload.delivery_address,notes=payload.notes,discount=payload.discount,freight=payload.freight,status="Rascunho");db.add(o);db.flush();subtotal=Decimal("0")
    for x in payload.items:
        p=db.get(Product,x.product_id)
        if not p:raise HTTPException(404,f"Produto {x.product_id} não encontrado.")
        unit_price=x.unit_price
        if unit_price is None:
            client_price=None
            if payload.client_id:
                client_price=db.scalar(select(ClientProductPrice).where(ClientProductPrice.client_id==payload.client_id,ClientProductPrice.active.is_(True),or_(ClientProductPrice.product_ref.in_([p.id,p.code]),ClientProductPrice.product_name==p.name)))
            unit_price=client_price.price if client_price is not None else p.price
        gross=Decimal(str(x.quantity))*Decimal(str(unit_price));total=gross*(Decimal("1")-Decimal(str(x.discount_percent))/Decimal("100"));subtotal+=total;o.items.append(SalesOrderItem(product_id=x.product_id,description=x.description or p.name,quantity=x.quantity,unit_price=unit_price,discount_percent=x.discount_percent,total=total))
    o.subtotal=subtotal;o.total=subtotal-Decimal(str(payload.discount))+Decimal(str(payload.freight));audit(db,module="Vendas",action="CRIAR",entity_type="sales_order",entity_id=o.id,description=o.code,user_id=user.id,user_name=user.full_name);db.commit();return out(load(db,o.id))

@router.post("/{order_id}/confirm",dependencies=[Depends(require_permission("sales.write"))])
def confirm(order_id:str,payload:SalesConfirmRequest,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    o=load(db,order_id)
    if not o:raise HTTPException(404,"Pedido não encontrado.")
    if o.status!="Rascunho":raise HTTPException(409,"Pedido já processado.")
    ops=[]
    for i in o.items:
        p=db.get(Product,i.product_id)
        if not p:continue
        available=Decimal(str(p.stock or 0))-Decimal(str(p.reserved_stock or 0));needed=Decimal(str(i.quantity))
        if available>=needed:reserve_stock(db,product_id=p.id,quantity=needed,location_id=p.location_id)
        elif p.manufacturing_enabled and payload.auto_create_production:
            sheet=db.scalar(select(TechnicalSheet).where(TechnicalSheet.product_id==p.id,TechnicalSheet.active.is_(True)).order_by(TechnicalSheet.version.desc()))
            op=create_production_order(db,ProductionOrderCreate(order_ref=o.code,product_id=p.id,technical_sheet_id=sheet.id if sheet else None,product_name=p.name,quantity=needed,production_mode="PRODUZIR_DO_ZERO"));i.production_order_id=op.id;ops.append(op.id)
        else:raise HTTPException(409,f"Estoque insuficiente para {p.name} e produção automática indisponível.")
    o.status="Confirmado"
    if payload.create_receivable and o.total>0:db.add(FinancialEntry(kind="Receita",description=f"Pedido {o.code}",category="Vendas",due_date=date.today(),amount=o.total,status="A receber",notes=f"Gerado automaticamente pelo pedido {o.code}."))
    audit(db,module="Vendas",action="CONFIRMAR",entity_type="sales_order",entity_id=o.id,description=f"{o.code}; OPs {len(ops)}",user_id=user.id,user_name=user.full_name);db.commit();return {"order":out(load(db,o.id)),"production_orders_created":ops}

@router.post("/{order_id}/ship",dependencies=[Depends(require_permission("sales.ship"))])
def ship(order_id:str,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    o=load(db,order_id)
    if not o:raise HTTPException(404,"Pedido não encontrado.")
    if o.status not in {"Confirmado","Pronto"}:raise HTTPException(409,"Pedido não está liberado para expedição.")
    for i in o.items:
        if i.production_order_id:
            op=db.get(ProductionOrder,i.production_order_id)
            if op and op.status!="Concluída":raise HTTPException(409,f"A produção de {i.description} ainda não foi concluída.")
        p=db.get(Product,i.product_id)
        if not p:continue
        release_reservation(db,product_id=p.id,quantity=i.quantity,location_id=p.location_id)
        move_stock(db,product_id=p.id,quantity=-Decimal(str(i.quantity)),movement_type="SAIDA_VENDA",location_id=p.location_id,unit_cost=p.cost,reference_type="sales_order",reference_id=o.id,notes=f"Expedição {o.code}",user_id=user.id)
    o.status="Expedido";delivery=Delivery(code=f"ENT-{uuid4().hex[:8].upper()}",client_id=o.client_id,order_ref=o.code,recipient_name=o.client_name or "Cliente",address=o.delivery_address or "",scheduled_date=date.today(),status="Agendada",notes=f"Gerada automaticamente pelo pedido {o.code}.");db.add(delivery);audit(db,module="Vendas",action="EXPEDIR",entity_type="sales_order",entity_id=o.id,description=o.code,user_id=user.id,user_name=user.full_name);db.commit();return {"order":out(load(db,o.id)),"delivery_id":delivery.id}
