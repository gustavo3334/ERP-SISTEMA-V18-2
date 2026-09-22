from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app


def _product(c, code):
    r = c.post("/api/v1/products", json={"code": code, "name": code, "stock": 0})
    assert r.status_code == 201, r.text
    return r.json()


def _location(c, name, code):
    r = c.post("/api/v1/stock-locations", json={"name": name, "address_code": code})
    assert r.status_code == 201, r.text
    return r.json()


def test_transfer_is_atomic_and_does_not_duplicate_product_stock():
    with TestClient(app) as client:
        product = _product(client, "TRF-001")
        loc_a = _location(client, "A", "A-01")
        loc_b = _location(client, "B", "B-01")

        r = client.post("/api/v1/inventory/movements", json={
            "product_id": product["id"],
            "location_id": loc_a["id"],
            "movement_type": "ENTRADA_AJUSTE",
            "quantity": 10,
            "unit_cost": 1,
        })
        assert r.status_code == 200, r.text

        r = client.post("/api/v1/inventory/transfer", json={
            "product_id": product["id"],
            "quantity": 4,
            "source_location_id": loc_a["id"],
            "destination_location_id": loc_b["id"],
            "notes": "teste",
        })
        assert r.status_code == 200, r.text

        balances = client.get(f"/api/v1/inventory/balances?product_id={product['id']}").json()
        by_loc = {x["location_id"]: Decimal(str(x["quantity"])) for x in balances}
        assert by_loc[loc_a["id"]] == Decimal("6")
        assert by_loc[loc_b["id"]] == Decimal("4")
        product_after = client.get(f"/api/v1/products/{product['id']}").json()
        assert Decimal(str(product_after["stock"])) == Decimal("10")


def test_transfer_rejects_reserved_or_insufficient_available():
    with TestClient(app) as client:
        product = _product(client, "TRF-002")
        loc_a = _location(client, "A2", "A-02")
        loc_b = _location(client, "B2", "B-02")
        client.post("/api/v1/inventory/movements", json={
            "product_id": product["id"],
            "location_id": loc_a["id"],
            "movement_type": "ENTRADA_AJUSTE",
            "quantity": 5,
        })
        client.post("/api/v1/inventory/reserve", json={
            "product_id": product["id"],
            "location_id": loc_a["id"],
            "quantity": 4,
        })
        r = client.post("/api/v1/inventory/transfer", json={
            "product_id": product["id"],
            "quantity": 2,
            "source_location_id": loc_a["id"],
            "destination_location_id": loc_b["id"],
        })
        assert r.status_code == 409
