from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.models import Client, ClientProductPrice, Product
from app.schemas_extended import FrontClientSyncPayload


router = APIRouter(prefix="/client-management", tags=["Clientes / Comercial"] )


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _client_state(db: Session, client: Client) -> dict[str, Any]:
    prices = db.scalars(
        select(ClientProductPrice)
        .where(ClientProductPrice.client_id == client.id, ClientProductPrice.active.is_(True))
        .order_by(ClientProductPrice.product_name.asc())
    ).all()
    return {
        "server": {
            "id": client.id,
            "legacy_id": client.legacy_id,
            "name": client.name,
            "document": client.document,
            "email": client.email,
            "phone": client.phone,
            "address": client.address,
            "status": client.status,
            "credit_limit": client.credit_limit,
            "preferred_payment": client.preferred_payment,
            "payment_methods": client.payment_methods_json or [],
            "purchase_history": client.purchase_history,
            "notes": client.notes,
            "active": client.active,
        },
        "front_payload": client.front_payload_json or {},
        "price_table": [
            {
                "id": row.id,
                "product_ref": row.product_ref,
                "product_name": row.product_name,
                "price": row.price,
            }
            for row in prices
        ],
    }


@router.get("/front/state", dependencies=[Depends(require_permission("clients.read"))])
def front_state(db: Session = Depends(get_db)):
    clients = db.scalars(select(Client).order_by(Client.name.asc())).all()
    return {"clients": [_client_state(db, client) for client in clients]}


@router.put("/sync/front", dependencies=[Depends(require_permission("clients.write"))])
def sync_front(payload: FrontClientSyncPayload, db: Session = Depends(get_db)):
    legacy_map: dict[str, str] = {}
    for raw in payload.clients:
        legacy_id = str(raw.get("id") or "").strip() or None
        document = str(raw.get("document") or "").strip()

        client = None
        if legacy_id:
            client = db.scalar(select(Client).where(Client.legacy_id == legacy_id))
        if client is None and document:
            client = db.scalar(select(Client).where(Client.document == document))
        if client is None:
            client = Client(name=str(raw.get("name") or "Cliente"), legacy_id=legacy_id)
            db.add(client)
            db.flush()

        client.legacy_id = legacy_id or client.legacy_id
        client.name = str(raw.get("name") or client.name or "Cliente")
        client.document = document
        client.email = str(raw.get("email") or "")
        client.phone = str(raw.get("phone") or "")
        client.address = str(raw.get("address") or "")
        client.status = str(raw.get("status") or "Ativo")
        client.credit_limit = _decimal(raw.get("creditLimit"))
        client.preferred_payment = str(raw.get("preferredPayment") or "")
        methods = raw.get("paymentMethods") or []
        if not isinstance(methods, list):
            methods = [str(methods)] if methods else []
        client.payment_methods_json = [str(item) for item in methods if str(item).strip()]
        client.purchase_history = str(raw.get("purchaseHistory") or "")
        client.notes = str(raw.get("notes") or "")
        client.active = client.status not in {"Inativo", "Bloqueado"}
        client.front_payload_json = raw
        db.flush()

        db.execute(delete(ClientProductPrice).where(ClientProductPrice.client_id == client.id))
        seen: set[str] = set()
        for item in raw.get("priceTable") or []:
            product_ref = str(item.get("productId") or item.get("productRef") or item.get("product") or "").strip()
            product_name = str(item.get("productName") or item.get("name") or "").strip()
            if not product_ref:
                product_ref = product_name
            if not product_ref or product_ref in seen:
                continue
            seen.add(product_ref)
            db.add(
                ClientProductPrice(
                    client_id=client.id,
                    product_ref=product_ref,
                    product_name=product_name,
                    price=_decimal(item.get("price")),
                    active=True,
                )
            )
        if legacy_id:
            legacy_map[legacy_id] = client.id

    db.commit()
    return {"status": "ok", "clients": len(payload.clients), "legacy_map": legacy_map}


@router.delete("/by-legacy/{legacy_id}", status_code=204, dependencies=[Depends(require_permission("clients.write"))])
def delete_by_legacy(legacy_id: str, db: Session = Depends(get_db)):
    client = db.scalar(select(Client).where(Client.legacy_id == legacy_id))
    if client is None:
        raise HTTPException(404, "Cliente não encontrado.")
    db.delete(client)
    db.commit()
    return None


@router.get("/{client_ref}/product-price/{product_ref}", dependencies=[Depends(require_permission("clients.read"))])
def resolve_product_price(client_ref: str, product_ref: str, db: Session = Depends(get_db)):
    client = db.scalar(
        select(Client).where(or_(Client.id == client_ref, Client.legacy_id == client_ref))
    )
    if client is None:
        raise HTTPException(404, "Cliente não encontrado.")

    price_row = db.scalar(
        select(ClientProductPrice).where(
            ClientProductPrice.client_id == client.id,
            ClientProductPrice.active.is_(True),
            or_(
                ClientProductPrice.product_ref == product_ref,
                ClientProductPrice.product_name.ilike(product_ref),
            ),
        )
    )
    if price_row is not None:
        return {
            "client_id": client.id,
            "product_ref": product_ref,
            "price": price_row.price,
            "source": "client_price_table",
        }

    product = db.scalar(
        select(Product).where(or_(Product.id == product_ref, Product.code == product_ref, Product.name.ilike(product_ref)))
    )
    return {
        "client_id": client.id,
        "product_ref": product_ref,
        "price": product.price if product is not None else Decimal("0"),
        "source": "product_default" if product is not None else "not_found",
    }
