from fastapi.testclient import TestClient

from app.main import app


def test_complete_front_state_persists():
    payload = {
        "payload": {
            "snapshot": {
                "schemaVersion": 2,
                "savedAt": "2026-07-24T20:00:00.000Z",
                "rhEmployees": [
                    {"id": "COL-TESTE", "name": "Teste Persistência"}
                ],
            }
        },
        "version": 2,
    }

    with TestClient(app) as client:
        saved = client.put(
            "/api/v1/front-state/sistema-completo",
            json=payload,
        )
        assert saved.status_code == 200

        loaded = client.get(
            "/api/v1/front-state/sistema-completo",
        )
        assert loaded.status_code == 200
        data = loaded.json()
        assert data["payload"]["snapshot"]["rhEmployees"][0]["id"] == "COL-TESTE"
