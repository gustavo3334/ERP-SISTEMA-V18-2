from fastapi.testclient import TestClient

from app.main import app


def test_client_crud():
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/clients",
            json={"name": "Cliente de teste"},
        )
        assert created.status_code == 201
        client_id = created.json()["id"]

        listed = client.get("/api/v1/clients")
        assert listed.status_code == 200
        assert any(item["id"] == client_id for item in listed.json())

        deleted = client.delete(f"/api/v1/clients/{client_id}")
        assert deleted.status_code == 204
