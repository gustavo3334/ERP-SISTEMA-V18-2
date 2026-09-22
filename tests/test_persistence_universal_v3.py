from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_snapshot_persists_major_front_modules_across_client_sessions():
    key = "auditoria-persistencia-universal"
    snapshot = {
        "schemaVersion": 3,
        "savedAt": "2026-07-29T10:00:00.000Z",
        "data": {"orders": [{"id": "PED-1"}], "quotes": [{"id": "ORC-1"}]},
        "enterpriseData": {
            "clients": [{"id": "CLI-1", "name": "Cliente real"}],
            "suppliers": [{"id": "FOR-1", "name": "Fornecedor real"}],
        },
        "engineeringData": {
            "products": [{"id": "PROD-1", "name": "Produto real"}],
            "orders": [{"id": "OP-1"}],
        },
        "technicalSheets": {"FT-1": {"id": "FT-1", "productId": "PROD-1"}},
        "deliveryData": [{"id": "ENT-1"}],
        "rhEmployees": [{"id": "COL-1", "name": "Colaborador real"}],
        "rhPieceRates": [{"id": "RATE-1", "employeeId": "COL-1", "rate": 5}],
        "permissionData": {"Administrador": {"Dashboard": {"visualizar": True}}},
        "universalCreatedRecords": [{"id": "LOCAL-1", "type": "Registro"}],
    }

    with TestClient(app) as client:
        created = client.put(
            f"/api/v1/front-state/{key}",
            json={"payload": {"snapshot": snapshot}, "version": 3, "base_revision": 0},
        )
        assert created.status_code == 200, created.text
        assert created.json()["revision"] == 1

    # Novo contexto de cliente simula uma nova sessão/navegador consumindo o mesmo DB.
    with TestClient(app) as client:
        loaded = client.get(f"/api/v1/front-state/{key}")
        assert loaded.status_code == 200
        restored = loaded.json()["payload"]["snapshot"]
        assert restored["enterpriseData"]["clients"][0]["id"] == "CLI-1"
        assert restored["engineeringData"]["products"][0]["id"] == "PROD-1"
        assert restored["technicalSheets"]["FT-1"]["id"] == "FT-1"
        assert restored["deliveryData"][0]["id"] == "ENT-1"
        assert restored["rhEmployees"][0]["id"] == "COL-1"
        assert restored["permissionData"]["Administrador"]["Dashboard"]["visualizar"] is True


def test_stale_or_blank_browser_cannot_overwrite_newer_server_state():
    key = "auditoria-concorrencia"
    with TestClient(app) as client:
        first = client.put(
            f"/api/v1/front-state/{key}",
            json={
                "payload": {"snapshot": {"schemaVersion": 3, "enterpriseData": {"clients": [{"id": "CLI-KEEP"}]}}},
                "version": 3,
                "base_revision": 0,
            },
        )
        assert first.status_code == 200
        revision = first.json()["revision"]

        second = client.put(
            f"/api/v1/front-state/{key}",
            json={
                "payload": {"snapshot": {"schemaVersion": 3, "enterpriseData": {"clients": [{"id": "CLI-NEW"}]}}},
                "version": 3,
                "base_revision": revision,
            },
        )
        assert second.status_code == 200
        assert second.json()["revision"] == revision + 1

        # Simula outro computador que ficou preso na revisão anterior e tenta salvar vazio.
        stale = client.put(
            f"/api/v1/front-state/{key}",
            json={
                "payload": {"snapshot": {"schemaVersion": 3, "enterpriseData": {"clients": []}}},
                "version": 3,
                "base_revision": revision,
            },
        )
        assert stale.status_code == 409

        current = client.get(f"/api/v1/front-state/{key}").json()
        assert current["payload"]["snapshot"]["enterpriseData"]["clients"][0]["id"] == "CLI-NEW"


def test_front_state_keeps_revision_history_and_can_restore():
    key = "auditoria-historico"
    with TestClient(app) as client:
        r1 = client.put(
            f"/api/v1/front-state/{key}",
            json={"payload": {"snapshot": {"value": "primeiro"}}, "version": 3, "base_revision": 0},
        ).json()["revision"]
        r2_resp = client.put(
            f"/api/v1/front-state/{key}",
            json={"payload": {"snapshot": {"value": "segundo"}}, "version": 3, "base_revision": r1},
        )
        assert r2_resp.status_code == 200
        r2 = r2_resp.json()["revision"]

        history = client.get(f"/api/v1/front-state/{key}/revisions?limit=10")
        assert history.status_code == 200
        revisions = [row["revision"] for row in history.json()]
        assert r2 in revisions and r1 in revisions

        restored = client.post(f"/api/v1/front-state/{key}/restore/{r1}")
        assert restored.status_code == 200
        assert restored.json()["payload"]["snapshot"]["value"] == "primeiro"
        assert restored.json()["revision"] == r2 + 1


def test_front_uses_single_server_authoritative_persistence_engine():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert 'const COMPLETE_KEY = "fp_erp_complete_state_v3"' in html
    assert 'const SERVER_STATE_KEY = "sistema-completo"' in html
    assert 'state.permissionData = clone(permissionData)' in html
    assert 'if (remote?.snapshot)' in html
    assert 'base_revision: serverRevision' in html
    assert 'fpLegacyFrontStateBridgeDisabled' in html
    assert 'const STATE_KEY = "default"' not in html
