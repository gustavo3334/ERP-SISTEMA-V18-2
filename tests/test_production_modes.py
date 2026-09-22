from fastapi.testclient import TestClient

from app.main import app


def test_production_modes_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/production-orders/options/production-modes")
        assert response.status_code == 200
        values = {item["value"] for item in response.json()}
        assert "PRODUZIR_DO_ZERO" in values
        assert "BAU_BLINDADO" in values
        assert "RETIRAR_ESTOQUE_VAZADO" in values


def test_vazado_stock_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/production-orders/options/vazado-stock")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_withdraw_vazado_from_stock_and_restore_on_delete():
    with TestClient(app) as client:
        created_product = client.post(
            "/api/v1/products",
            json={
                "code": "VAZADO-TESTE",
                "name": "Baú vazado teste",
                "item_type": "Pré-fabricado",
                "unit": "UN",
                "stock": 5,
                "cost": 10
            },
        )
        assert created_product.status_code == 201
        product = created_product.json()

        order_response = client.post(
            "/api/v1/production-orders",
            json={
                "production_mode": "RETIRAR_ESTOQUE_VAZADO",
                "source_stock_product_id": product["id"],
                "product_name": "Baú acabado teste",
                "quantity": 2
            },
        )
        assert order_response.status_code == 201
        order = order_response.json()
        assert order["production_mode"] == "RETIRAR_ESTOQUE_VAZADO"
        assert any(stage["name"] == "RETIRADA DO ESTOQUE DE VAZADO" for stage in order["stages"])

        after_withdraw = client.get(f"/api/v1/products/{product['id']}")
        assert float(after_withdraw.json()["stock"]) == 3.0

        deleted = client.delete(f"/api/v1/production-orders/{order['id']}")
        assert deleted.status_code == 204

        after_delete = client.get(f"/api/v1/products/{product['id']}")
        assert float(after_delete.json()["stock"]) == 5.0


def test_blindado_creates_specific_stage():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/production-orders",
            json={
                "production_mode": "BAU_BLINDADO",
                "product_name": "Baú blindado teste",
                "quantity": 1
            },
        )
        assert response.status_code == 201
        order = response.json()
        assert order["production_mode"] == "BAU_BLINDADO"
        assert any(stage["name"] == "BLINDAGEM" for stage in order["stages"])
