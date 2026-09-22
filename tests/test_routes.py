from fastapi.testclient import TestClient

from app.main import app


def test_route_provider():
    with TestClient(app) as client:
        response = client.get("/api/v1/routes/provider")
        assert response.status_code == 200
        assert response.json()["effective"] in {"google", "osm"}
