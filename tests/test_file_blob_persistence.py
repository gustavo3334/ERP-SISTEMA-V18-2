from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_employee_document_survives_missing_local_file():
    with TestClient(app) as client:
        synced = client.put(
            "/api/v1/employees/sync/front",
            json={
                "employees": [{"id": "COL-FILE-PERSIST", "name": "Arquivo Persistente", "status": "Ativo"}],
                "piece_rates": [],
                "production_entries": [],
            },
        )
        assert synced.status_code == 200, synced.text
        employee_id = synced.json()["legacy_map"]["COL-FILE-PERSIST"]

        original = b"documento-persistente-render"
        uploaded = client.post(
            "/api/v1/files/employee-document",
            data={"employee_id": employee_id, "document_type": "RG"},
            files={"file": ("rg-teste.pdf", original, "application/pdf")},
        )
        assert uploaded.status_code == 200, uploaded.text
        payload = uploaded.json()
        assert payload["persistent"] is True
        file_id = payload["id"]

        # Remove propositalmente a cópia local para simular redeploy/restart no Render.
        from app.database import SessionLocal
        from app.models_extended import StoredFile

        with SessionLocal() as db:
            stored = db.get(StoredFile, file_id)
            assert stored is not None
            local_path = Path(stored.storage_path)
            local_path.unlink(missing_ok=True)
            assert stored.content_blob == original

        downloaded = client.get(f"/api/v1/files/{file_id}/download")
        assert downloaded.status_code == 200
        assert downloaded.content == original


def test_front_sync_reuses_uploaded_document_record_instead_of_duplicating():
    with TestClient(app) as client:
        synced = client.put(
            "/api/v1/employees/sync/front",
            json={
                "employees": [{"id": "COL-DOC-SYNC", "name": "Documento Sincronizado", "status": "Ativo"}],
                "piece_rates": [],
                "production_entries": [],
            },
        )
        assert synced.status_code == 200
        employee_id = synced.json()["legacy_map"]["COL-DOC-SYNC"]

        upload = client.post(
            "/api/v1/files/employee-document",
            data={"employee_id": employee_id, "document_type": "CPF"},
            files={"file": ("cpf.pdf", b"cpf-test", "application/pdf")},
        )
        assert upload.status_code == 200
        uploaded = upload.json()

        resync = client.put(
            "/api/v1/employees/sync/front",
            json={
                "employees": [{
                    "id": "COL-DOC-SYNC",
                    "name": "Documento Sincronizado",
                    "status": "Ativo",
                    "documents": [{
                        "id": "DOC-FRONT-1",
                        "type": "CPF",
                        "status": "Recebido",
                        "storedFileId": uploaded["id"],
                        "_serverDocumentId": uploaded["document_id"],
                    }],
                }],
                "piece_rates": [],
                "production_entries": [],
            },
        )
        assert resync.status_code == 200, resync.text

        state = client.get("/api/v1/employees/front/state")
        assert state.status_code == 200
        employee = next(
            item for item in state.json()["employees"]
            if item["server"]["legacy_id"] == "COL-DOC-SYNC"
        )
        docs = [doc for doc in employee["documents"] if doc["legacy_id"] == "DOC-FRONT-1"]
        assert len(docs) == 1
        assert docs[0]["stored_file_id"] == uploaded["id"]
