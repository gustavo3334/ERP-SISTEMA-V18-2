from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, JSON, String, create_engine, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DB_URL = os.getenv("MOCK_ERP_DATABASE_URL", "sqlite:///./mock_erp.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def now():
    return datetime.now(timezone.utc)


class Entity(Base):
    __tablename__ = "mock_entities"
    kind = Column(String(80), primary_key=True)
    id = Column(String(64), primary_key=True)
    data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=now)
    updated_at = Column(DateTime(timezone=True), default=now)


Base.metadata.create_all(engine)

USERS = {
    "admin@facilpedido.local": {"id": "USR-ADMIN", "email": "admin@facilpedido.local", "full_name": "Administrador", "role": "administrator", "password": "TroqueEstaSenha123!", "active": True},
    "rh@facilpedido.local": {"id": "USR-RH", "email": "rh@facilpedido.local", "full_name": "Responsável RH", "role": "hr", "password": "RHcatalogo123!", "active": True},
    "vendas@facilpedido.local": {"id": "USR-SALES", "email": "vendas@facilpedido.local", "full_name": "Vendedor Teste", "role": "sales", "password": "Vendas123!", "active": True},
}
TOKENS: dict[str, str] = {}

ROLE_PERMS = {
    "administrator": ["*"],
    "manager": ["products:manage", "clients:manage", "quotes:manage", "stock:manage", "deliveries:manage", "financial-entries:manage", "production-orders:manage", "users:read"],
    "hr": ["employees:manage", "payroll:manage", "dashboard:read"],
    "sales": ["products:read", "clients:manage", "quotes:manage", "deliveries:manage", "dashboard:read"],
}


def seed():
    s = SessionLocal()
    try:
        def put(kind, data):
            if not s.get(Entity, {"kind": kind, "id": data["id"]}):
                s.add(Entity(kind=kind, id=data["id"], data=data))
        put("category", {"id": "CAT-SALA", "name": "Sala", "item_type": "Produto acabado", "description": "", "active": True})
        put("location", {"id": "LOC-MATRIZ", "name": "Matriz", "warehouse": "Depósito", "aisle": "", "rack": "", "shelf": "", "address_code": "MATRIZ", "description": "", "active": True})
        put("product", {
            "id": "PRD-SOFA-TESTE", "code": "SOF-001", "name": "Sofá de teste", "description": "Produto de teste para validar integração e fotos.",
            "item_type": "Produto acabado", "category_id": "CAT-SALA", "supplier_id": None, "location_id": "LOC-MATRIZ",
            "color": "Bege", "size": "Padrão", "unit": "UN", "cost": 0, "technical_cost": 0, "price": 0,
            "stock": 0, "reserved_stock": 0, "min_stock": 0, "base_stock": 0, "manufacturing_enabled": True, "active": True,
        })
        s.commit()
    finally:
        s.close()
seed()

app = FastAPI(title="ERP principal mock para teste", version="2.1-test")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


def token_for(email: str) -> str:
    token = base64.urlsafe_b64encode(f"{email}:{secrets.token_hex(8)}".encode()).decode().rstrip("=")
    TOKENS[token] = email
    return token


def auth(request: Request) -> dict[str, Any]:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "Não autenticado")
    token = header.split(" ", 1)[1]
    email = TOKENS.get(token)
    u = USERS.get(email or "")
    if not u:
        raise HTTPException(401, "Token inválido")
    return u


def clean_user(u):
    return {k: v for k, v in u.items() if k != "password"}


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "database": "connected", "mode": "mock"}


class Login(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str = ""


@app.post("/api/v1/auth/login")
def login(body: Login):
    email = (body.email or body.username or "").strip().lower()
    u = USERS.get(email)
    if not u or body.password != u["password"]:
        raise HTTPException(401, "Usuário ou senha inválidos.")
    return {"token": token_for(email), "token_type": "bearer", "user": clean_user(u), "permissions": ROLE_PERMS.get(u["role"], [])}


@app.get("/api/v1/auth/me")
def me(request: Request):
    return clean_user(auth(request))


def rows(kind: str, limit=500):
    s=SessionLocal()
    try:
        return [dict(x.data or {}) for x in s.execute(select(Entity).where(Entity.kind==kind).limit(limit)).scalars().all()]
    finally: s.close()


def get(kind, id):
    s=SessionLocal()
    try:
        x=s.get(Entity,{"kind":kind,"id":id})
        return dict(x.data or {}) if x else None
    finally:s.close()


def save(kind, data, item_id=None):
    s=SessionLocal()
    try:
        item_id=str(item_id or data.get("id") or uuid.uuid4())
        obj=s.get(Entity,{"kind":kind,"id":item_id})
        d={**(dict(obj.data or {}) if obj else {}), **data, "id":item_id}
        if obj: obj.data=d; obj.updated_at=now()
        else: s.add(Entity(kind=kind,id=item_id,data=d,created_at=now(),updated_at=now()))
        s.commit(); return d
    finally:s.close()


def remove(kind,id):
    s=SessionLocal()
    try:
        obj=s.get(Entity,{"kind":kind,"id":id})
        if not obj: raise HTTPException(404,"Registro não encontrado.")
        s.delete(obj);s.commit()
    finally:s.close()

RESOURCE_KIND={"products":"product","product-variants":"variant","categories":"category","stock-locations":"location","clients":"client","deliveries":"delivery","financial-entries":"financial","production-orders":"production"}

for resource,kind in RESOURCE_KIND.items():
    def mk_list(res=resource,k=kind):
        async def fn(request:Request,limit:int=500,offset:int=0,q:str|None=None):
            auth(request); data=rows(k,limit+offset)[offset:offset+limit]
            if q:
                nq=q.lower();data=[x for x in data if nq in json.dumps(x,ensure_ascii=False).lower()]
            return data
        fn.__name__=f"list_{res.replace('-','_')}";return fn
    def mk_create(res=resource,k=kind):
        async def fn(request:Request):
            auth(request);body=await request.json()
            if res=="deliveries" and not body.get("code"): body["code"]=f"ENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if res=="production-orders" and not body.get("code"): body["code"]=f"OP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return save(k,body)
        fn.__name__=f"create_{res.replace('-','_')}";return fn
    def mk_get(res=resource,k=kind):
        async def fn(item_id:str,request:Request):
            auth(request);d=get(k,item_id)
            if not d:raise HTTPException(404,"Registro não encontrado.")
            return d
        fn.__name__=f"get_{res.replace('-','_')}";return fn
    def mk_put(res=resource,k=kind):
        async def fn(item_id:str,request:Request): auth(request);return save(k,await request.json(),item_id)
        fn.__name__=f"put_{res.replace('-','_')}";return fn
    def mk_del(res=resource,k=kind):
        async def fn(item_id:str,request:Request): auth(request);remove(k,item_id);return Response(status_code=204)
        fn.__name__=f"del_{res.replace('-','_')}";return fn
    app.add_api_route(f"/api/v1/{resource}",mk_list(),methods=["GET"])
    app.add_api_route(f"/api/v1/{resource}",mk_create(),methods=["POST"])
    app.add_api_route(f"/api/v1/{resource}/{{item_id}}",mk_get(),methods=["GET"])
    app.add_api_route(f"/api/v1/{resource}/{{item_id}}",mk_put(),methods=["PUT"])
    app.add_api_route(f"/api/v1/{resource}/{{item_id}}",mk_del(),methods=["DELETE"])


@app.get("/api/v1/users")
def list_users(request: Request):
    auth(request)
    return [{**clean_user(u), "created_at": now().isoformat(), "updated_at": now().isoformat()} for u in USERS.values()]


@app.post("/api/v1/users")
async def create_user(request: Request):
    auth(request); body=await request.json();email=str(body.get("email") or "").lower()
    if not email or email in USERS: raise HTTPException(409,"Usuário inválido ou já existente")
    USERS[email]={"id":str(uuid.uuid4()),"email":email,"full_name":body.get("full_name") or "","role":body.get("role") or "viewer","password":body.get("password") or "12345678","active":body.get("active",True)}
    return clean_user(USERS[email])


@app.put("/api/v1/users/{item_id}")
async def update_user(item_id:str,request:Request):
    auth(request);body=await request.json();u=next((u for u in USERS.values() if u["id"]==item_id),None)
    if not u:raise HTTPException(404,"Usuário não encontrado")
    for k in ("full_name","role","active","password"):
        if k in body and body[k] is not None:u[k]=body[k]
    return clean_user(u)


@app.get("/api/v1/quotes")
def quote_list(request:Request,limit:int=500,offset:int=0):auth(request);return rows("quote",limit+offset)[offset:offset+limit]

@app.post("/api/v1/quotes")
async def quote_create(request:Request):
    auth(request);b=await request.json();items=[];total=0.0
    for i in b.get("items") or []:
        q=float(i.get("quantity") or 0);p=float(i.get("unit_price") or 0);d=float(i.get("discount") or 0);t=q*p*(1-d/100);items.append({**i,"total":round(t,2)});total+=t
    b={**b,"code":b.get("code") or f"ORC-{datetime.now().strftime('%Y%m%d%H%M%S')}","items":items,"total":round(total,2)}
    return save("quote",b)

@app.get("/api/v1/quotes/{item_id}")
def quote_get(item_id:str,request:Request):auth(request);d=get("quote",item_id);return d if d else (_ for _ in ()).throw(HTTPException(404,"Orçamento não encontrado"))

@app.put("/api/v1/quotes/{item_id}")
async def quote_put(item_id:str,request:Request):auth(request);return save("quote",await request.json(),item_id)

@app.delete("/api/v1/quotes/{item_id}")
def quote_del(item_id:str,request:Request):auth(request);remove("quote",item_id);return Response(status_code=204)


@app.get("/api/v1/stock/balance")
def stock_balance(request:Request,limit:int=500,offset:int=0,only_below_minimum:bool=False):
    auth(request);out=[]
    for p in rows("product",limit+offset)[offset:offset+limit]:
        stock=float(p.get("stock") or 0);reserved=float(p.get("reserved_stock") or 0);minimum=float(p.get("min_stock") or 0);available=stock-reserved
        if only_below_minimum and available>=minimum:continue
        out.append({"product_id":p["id"],"code":p.get("code"),"name":p.get("name"),"unit":p.get("unit") or "UN","stock":stock,"reserved_stock":reserved,"available":available,"min_stock":minimum,"below_minimum":available<minimum,"location_id":p.get("location_id")})
    return out

@app.post("/api/v1/stock/adjust")
async def stock_adjust(request:Request):
    auth(request);b=await request.json();p=get("product",b.get("product_id"))
    if not p:raise HTTPException(404,"Produto não encontrado")
    p["stock"]=float(b.get("target_quantity") or 0);save("product",p,p["id"])
    return {"id":str(uuid.uuid4()),"product_id":p["id"],"movement_type":"AJUSTE","quantity":p["stock"],"balance_after":p["stock"]}

@app.post("/api/v1/stock/movements")
async def stock_movement(request:Request):
    auth(request);b=await request.json();p=get("product",b.get("product_id"))
    if not p:raise HTTPException(404,"Produto não encontrado")
    qty=float(b.get("quantity") or 0);typ=b.get("movement_type")
    stock=float(p.get("stock") or 0);reserved=float(p.get("reserved_stock") or 0)
    if typ=="RESERVA":
        if qty>stock-reserved:raise HTTPException(422,"Estoque disponível insuficiente")
        reserved+=qty
    elif typ=="LIBERACAO_RESERVA":reserved=max(0,reserved-qty)
    elif typ=="ENTRADA":stock+=qty
    elif typ=="SAIDA":stock=max(0,stock-qty)
    p["stock"]=stock;p["reserved_stock"]=reserved;save("product",p,p["id"])
    return {"id":str(uuid.uuid4()),**b,"balance_after":stock,"reference_type":"manual","reference_id":None,"created_by":"mock","created_at":now().isoformat()}

@app.get("/")
def root():return {"name":"ERP principal mock","api":"/api/v1","users":["admin@facilpedido.local","rh@facilpedido.local","vendas@facilpedido.local"]}
