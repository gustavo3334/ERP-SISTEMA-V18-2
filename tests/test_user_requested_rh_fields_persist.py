from fastapi.testclient import TestClient

from app.main import app


def test_all_user_requested_rh_fields_roundtrip():
    payload = {
        "legacy_id": "COL-REQUISITOS-001",
        "full_name": "Colaborador Requisitos",
        "collaborator_model": "MEI",
        "employment_category": "MEI",
        "employee_type": "Operacional",
        "status": "Ativo",
        "cpf": "11122233344",
        "rg": "123456789",
        "voter_title": "123456789012",
        "voter_zone": "100",
        "voter_section": "200",
        "phone_primary": "11999990000",
        "phone_secondary": "11888880000",
        "photo_url": "https://example.invalid/foto.jpg",
        "position": "Tapeceiro",
        "sector": "Tapeçaria",
        "start_date": "2026-07-20",
        "registration_date": "2026-07-25",
        "salary": "2500.00",
        "fixed_bonus": "200.00",
        "variable_bonus": "100.00",
        "address": {
            "cep": "07000000",
            "street": "Rua Teste",
            "number": "10",
            "neighborhood": "Centro",
            "city": "Guarulhos",
            "state": "SP",
            "residence_type": "Apartamento",
            "apartment": "42",
            "block": "B",
            "floor": "4",
            "condominium": "Condomínio Teste",
        },
        "contacts": [
            {"contact_type": "Emergência", "name": "Contato 1", "relationship": "Irmã", "phone": "11777770000", "priority": 1},
            {"contact_type": "Emergência", "name": "Contato 2", "relationship": "Pai", "phone": "11666660000", "priority": 2},
        ],
        "health": {
            "has_disease": True,
            "conditions": "Condição teste",
            "under_treatment": True,
            "treatment": "Tratamento teste",
            "continuous_medication": True,
            "medication": "Medicamento teste",
            "can_provide_medication": True,
            "authorized_medication": "Medicamento autorizado",
            "emergency_notes": "Orientação teste",
        },
        "mei": {
            "cnpj": "11222333000144",
            "legal_name": "MEI Teste LTDA",
            "trade_name": "MEI Teste",
        },
        "dependents": [
            {
                "legacy_id": "DEP-REQ-1",
                "name": "Filho Teste",
                "birth_date": "2020-03-10",
                "relationship": "Filho",
                "alimony": {
                    "active": True,
                    "agreement_type": "Acordo verbal",
                    "calculation_type": "Valor fixo",
                    "fixed_amount": "350.00",
                    "beneficiary": "Responsável teste",
                },
            }
        ],
        "bank_accounts": [
            {
                "bank": "Banco Teste",
                "agency": "1234",
                "account": "123456",
                "account_digit": "7",
                "pix_type": "Telefone",
                "pix_key": "11999990000",
                "pix_institution": "Instituição PIX",
                "portability": True,
                "origin_bank": "Banco Origem",
                "destination_bank": "Banco Destino",
                "receiving_bank": "Banco Recebedor",
                "is_primary": True,
            }
        ],
        "bonuses": [
            {"legacy_id": "BON-REQ-1", "bonus_type": "Produtividade", "amount": "125.50", "recurring": True}
        ],
        "transport_plan": {
            "company_address": "Rodovia João Afonso de Souza Castellano, 1800",
            "employee_address": "Rua Teste, 10, Guarulhos - SP",
            "working_days": 22,
            "legs": [
                {"transport_type": "Ônibus", "line": "001", "fare": "5.25", "uses_per_day": "2"}
            ],
        },
    }

    with TestClient(app) as client:
        created = client.post("/api/v1/employees", json=payload)
        assert created.status_code == 201, created.text
        employee_id = created.json()["id"]

        loaded = client.get(f"/api/v1/employees/{employee_id}")
        assert loaded.status_code == 200
        data = loaded.json()

        assert data["phone_secondary"] == "11888880000"
        assert data["voter_title"] == "123456789012"
        assert data["registration_date"] == "2026-07-25"
        assert data["address"]["apartment"] == "42"
        assert data["address"]["block"] == "B"
        assert len(data["contacts"]) == 2
        assert data["health"]["continuous_medication"] is True
        assert data["health"]["can_provide_medication"] is True
        assert data["mei"]["cnpj"] == "11222333000144"
        assert data["dependents"][0]["alimony"]["agreement_type"] == "Acordo verbal"
        assert data["bank_accounts"][0]["portability"] is True
        assert data["bank_accounts"][0]["pix_institution"] == "Instituição PIX"
        assert float(data["bonuses"][0]["amount"]) == 125.50
        assert data["transport_plan"]["company_address"] == "Rodovia João Afonso de Souza Castellano, 1800"
