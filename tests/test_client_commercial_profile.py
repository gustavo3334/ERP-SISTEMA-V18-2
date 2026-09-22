from fastapi.testclient import TestClient

from app.main import app


def test_client_payment_methods_and_price_table_persist():
    with TestClient(app) as client:
        payload = {
            "clients": [
                {
                    "id": "CLI-CUSTOM-001",
                    "name": "Cliente Tabela Especial",
                    "document": "12345678000101",
                    "phone": "11999990000",
                    "email": "cliente@example.com",
                    "address": "Rua Teste, 100",
                    "status": "Ativo",
                    "creditLimit": 10000,
                    "paymentMethods": ["PIX", "Cartão de crédito", "Boleto"],
                    "preferredPayment": "PIX",
                    "purchaseHistory": "Cliente atacadista",
                    "priceTable": [
                        {
                            "productId": "PRD-BAU-138",
                            "productName": "BAU 138",
                            "price": 320,
                        }
                    ],
                }
            ]
        }
        synced = client.put("/api/v1/client-management/sync/front", json=payload)
        assert synced.status_code == 200, synced.text
        assert synced.json()["legacy_map"]["CLI-CUSTOM-001"]

        state = client.get("/api/v1/client-management/front/state")
        assert state.status_code == 200, state.text
        row = next(
            item
            for item in state.json()["clients"]
            if item["server"]["legacy_id"] == "CLI-CUSTOM-001"
        )
        assert row["server"]["preferred_payment"] == "PIX"
        assert row["server"]["payment_methods"] == ["PIX", "Cartão de crédito", "Boleto"]
        assert float(row["price_table"][0]["price"]) == 320.0

        resolved = client.get(
            "/api/v1/client-management/CLI-CUSTOM-001/product-price/PRD-BAU-138"
        )
        assert resolved.status_code == 200, resolved.text
        assert float(resolved.json()["price"]) == 320.0
        assert resolved.json()["source"] == "client_price_table"

        deleted = client.delete("/api/v1/client-management/by-legacy/CLI-CUSTOM-001")
        assert deleted.status_code == 204, deleted.text


def test_sales_order_uses_client_price_when_unit_price_is_omitted():
    with TestClient(app) as client:
        product = client.post(
            "/api/v1/products",
            json={
                "code": "BAU-CUSTOM-138",
                "name": "BAU 138 preço cliente",
                "item_type": "Produto acabado",
                "unit": "UN",
                "cost": "100",
                "technical_cost": "100",
                "price": "410",
                "stock": "10",
                "reserved_stock": "0",
                "min_stock": "0",
                "base_stock": "0",
                "manufacturing_enabled": False,
                "active": True,
            },
        )
        assert product.status_code == 201, product.text
        product_id = product.json()["id"]

        synced = client.put(
            "/api/v1/client-management/sync/front",
            json={
                "clients": [
                    {
                        "id": "CLI-SALES-CUSTOM",
                        "name": "Cliente preço 320",
                        "document": "98765432000199",
                        "paymentMethods": ["PIX", "Boleto"],
                        "preferredPayment": "Boleto",
                        "priceTable": [
                            {
                                "productId": product_id,
                                "productName": "BAU 138 preço cliente",
                                "price": 320,
                            }
                        ],
                    }
                ]
            },
        )
        assert synced.status_code == 200, synced.text
        client_id = synced.json()["legacy_map"]["CLI-SALES-CUSTOM"]

        order = client.post(
            "/api/v1/sales-orders",
            json={
                "client_id": client_id,
                "client_name": "Cliente preço 320",
                "payment_method": "Boleto",
                "items": [{"product_id": product_id, "quantity": "2"}],
            },
        )
        assert order.status_code == 201, order.text
        item = order.json()["items"][0]
        assert float(item["unit_price"]) == 320.0
        assert float(order.json()["subtotal"]) == 640.0

        client.delete("/api/v1/client-management/by-legacy/CLI-SALES-CUSTOM")
        client.delete(f"/api/v1/products/{product_id}")
