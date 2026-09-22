from __future__ import annotations
from datetime import date
from decimal import Decimal
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session,selectinload
from app.audit_service import audit
from app.database import get_db
from app.dependencies import get_current_user,require_permission
from app.inventory_service import move_stock
from app.models import FinancialEntry,Product,Supplier
from app.models_extended import PurchaseOrder,PurchaseOrderItem
from app.schemas import CurrentUser
from app.schemas_extended import PurchaseOrderCreate,ReceivePurchaseRequest

router=APIRouter(prefix="/purchase-orders",tags=["Compras"])

class PurchaseOrderUpdatePayload(BaseModel):
    supplier_id: str | None = None
    expected_date: date | None = None
    payment_terms: str | None = None
    notes: str | None = None
    discount: Decimal | None = None
    freight: Decimal | None = None
    status: str | None = None
def new_code():return f"OC-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
def load(db,id):return db.scalar(select(PurchaseOrder).where(PurchaseOrder.id==id).options(selectinload(PurchaseOrder.items)))
def out(o):return {"id":o.id,"code":o.code,"supplier_id":o.supplier_id,"issue_date":o.issue_date,"expected_date":o.expected_date,"status":o.status,"payment_terms":o.payment_terms,"notes":o.notes,"subtotal":o.subtotal,"discount":o.discount,"freight":o.freight,"total":o.total,"items":[{"id":i.id,"product_id":i.product_id,"description":i.description,"quantity":i.quantity,"received_quantity":i.received_quantity,"unit_cost":i.unit_cost,"total":i.total,"location_id":i.location_id} for i in o.items]}

@router.get("",dependencies=[Depends(require_permission("purchasing.read"))])
def list_orders(db:Session=Depends(get_db)):
    return [out(x) for x in db.scalars(select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).order_by(PurchaseOrder.created_at.desc())).unique().all()]


@router.get("/{order_id}",dependencies=[Depends(require_permission("purchasing.read"))])
def get_order(order_id:str,db:Session=Depends(get_db)):
    o=load(db,order_id)
    if not o:raise HTTPException(404,"Ordem de compra não encontrada.")
    return out(o)

@router.post("",status_code=201,dependencies=[Depends(require_permission("purchasing.write"))])
def create(payload:PurchaseOrderCreate,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    o=PurchaseOrder(code=new_code(),supplier_id=payload.supplier_id,expected_date=payload.expected_date,payment_terms=payload.payment_terms,notes=payload.notes,discount=payload.discount,freight=payload.freight,status="Aberta");db.add(o);db.flush();subtotal=Decimal("0")
    for x in payload.items:
        p=db.get(Product,x.product_id)
        if not p:raise HTTPException(404,f"Produto {x.product_id} não encontrado.")
        total=Decimal(str(x.quantity))*Decimal(str(x.unit_cost));subtotal+=total;o.items.append(PurchaseOrderItem(product_id=x.product_id,description=x.description or p.name,quantity=x.quantity,unit_cost=x.unit_cost,total=total,location_id=x.location_id or p.location_id))
    o.subtotal=subtotal;o.total=subtotal-Decimal(str(payload.discount))+Decimal(str(payload.freight));audit(db,module="Compras",action="CRIAR",entity_type="purchase_order",entity_id=o.id,description=o.code,user_id=user.id,user_name=user.full_name);db.commit();return out(load(db,o.id))

@router.put("/{order_id}",dependencies=[Depends(require_permission("purchasing.write"))])
def update_order(order_id:str,payload:PurchaseOrderUpdatePayload,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    o=load(db,order_id)
    if not o:raise HTTPException(404,"Ordem de compra não encontrada.")
    changes=payload.model_dump(exclude_unset=True)
    if "supplier_id" in changes and changes["supplier_id"]:
        if db.get(Supplier,changes["supplier_id"]) is None:raise HTTPException(404,"Fornecedor não encontrado.")
    for key,value in changes.items():
        setattr(o,key,value)
    if "discount" in changes or "freight" in changes:
        o.total=Decimal(str(o.subtotal or 0))-Decimal(str(o.discount or 0))+Decimal(str(o.freight or 0))
    audit(db,module="Compras",action="ATUALIZAR",entity_type="purchase_order",entity_id=o.id,description=o.code,user_id=user.id,user_name=user.full_name)
    db.commit()
    return out(load(db,o.id))


@router.post("/{order_id}/receive",dependencies=[Depends(require_permission("purchasing.receive"))])
def receive(order_id:str,payload:ReceivePurchaseRequest,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    o=load(db,order_id)
    if not o:raise HTTPException(404,"Ordem de compra não encontrada.")
    if o.status in {"Cancelada","Recebida"}:raise HTTPException(409,f"Ordem está {o.status}.")
    requested={x.item_id:Decimal(str(x.quantity)) for x in payload.items};value=Decimal("0")
    for i in o.items:
        q=requested.get(i.id,Decimal("0"));remaining=Decimal(str(i.quantity))-Decimal(str(i.received_quantity))
        if q<=0:continue
        if q>remaining:raise HTTPException(422,f"Quantidade excede o saldo de {i.description}.")
        i.received_quantity=Decimal(str(i.received_quantity))+q;value+=q*Decimal(str(i.unit_cost));move_stock(db,product_id=i.product_id,quantity=q,movement_type="ENTRADA_COMPRA",location_id=i.location_id,unit_cost=i.unit_cost,reference_type="purchase_order",reference_id=o.id,notes=f"Recebimento {o.code}",user_id=user.id)
    o.status="Recebida" if all(Decimal(str(i.received_quantity))>=Decimal(str(i.quantity)) for i in o.items) else "Parcialmente recebida"
    if payload.create_payable and value>0:db.add(FinancialEntry(kind="Despesa",description=f"Compra {o.code}",category="Compras",due_date=o.expected_date or date.today(),amount=value,status="A pagar",notes=f"Gerado automaticamente pela ordem {o.code}."))
    audit(db,module="Compras",action="RECEBER",entity_type="purchase_order",entity_id=o.id,description=f"Recebimento {value}",user_id=user.id,user_name=user.full_name);db.commit();return out(load(db,o.id))


@router.post("/{order_id}/cancel",dependencies=[Depends(require_permission("purchasing.write"))])
def cancel(order_id:str,db:Session=Depends(get_db),user:CurrentUser=Depends(get_current_user)):
    o=load(db,order_id)
    if not o:raise HTTPException(404,"Ordem de compra não encontrada.")
    if o.status=="Cancelada":return out(o)
    if any(Decimal(str(i.received_quantity or 0))>0 for i in o.items):
        raise HTTPException(409,"Compra com recebimento não pode ser cancelada diretamente. Faça o estorno de estoque/financeiro conforme o processo da empresa.")
    o.status="Cancelada"
    audit(db,module="Compras",action="CANCELAR",entity_type="purchase_order",entity_id=o.id,description=o.code,user_id=user.id,user_name=user.full_name)
    db.commit();return out(load(db,o.id))
