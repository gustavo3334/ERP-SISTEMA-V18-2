from fastapi.testclient import TestClient

from app.main import app


def test_environment_endpoint_exists():
    with TestClient(app) as client:
        response = client.get("/api/v1/system/environment")
        assert response.status_code == 200
        payload = response.json()
        assert "environment" in payload
        assert "homologation" in payload
        assert "database" in payload
