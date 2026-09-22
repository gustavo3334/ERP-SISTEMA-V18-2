from fastapi.testclient import TestClient
from app.main import app


def test_front_state_recovers_employee_from_relational_db():
    front_employee={"id":"COL-AUTH-001","name":"Colaborador Persistente","cpf":"00000000000","position":"Auxiliar Administrativo","sector":"Recursos Humanos","type":"Administrativo","status":"Ativo","employmentCategory":"Registrado","collaboratorModel":"Pessoa física","salary":1800,"phonePrimary":"11999999999","personal":{"nationality":"Brasileira"},"dependents":[],"bonuses":[],"documents":[]}
    with TestClient(app) as client:
        synced=client.put("/api/v1/employees/sync/front",json={"employees":[front_employee],"piece_rates":[],"production_entries":[]})
        assert synced.status_code==200,synced.text
        assert synced.json()["legacy_map"]["COL-AUTH-001"]
        state=client.get("/api/v1/employees/front/state")
        assert state.status_code==200,state.text
        recovered=next(item for item in state.json()["employees"] if item["server"]["legacy_id"]=="COL-AUTH-001")
        assert recovered["server"]["full_name"]=="Colaborador Persistente"
        assert recovered["server"]["employee_type"]=="Administrativo"
        assert recovered["front_payload"]["type"]=="Administrativo"
        assert recovered["front_payload"]["phonePrimary"]=="11999999999"


def test_delete_employee_by_legacy_id():
    with TestClient(app) as client:
        created=client.put("/api/v1/employees/sync/front",json={"employees":[{"id":"COL-DELETE-001","name":"Excluir Persistente","status":"Ativo"}],"piece_rates":[],"production_entries":[]})
        assert created.status_code==200
        deleted=client.delete("/api/v1/employees/by-legacy/COL-DELETE-001")
        assert deleted.status_code==204,deleted.text
        listing=client.get("/api/v1/employees")
        assert listing.status_code==200
        assert not any(x["legacy_id"]=="COL-DELETE-001" for x in listing.json())
