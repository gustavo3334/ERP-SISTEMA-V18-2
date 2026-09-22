from fastapi.testclient import TestClient
from app.main import app


def test_front_rh_sync_populates_relational_database():
    with TestClient(app) as c:
        payload={'employees':[{'id':'RH-FRONT-1','name':'Pessoa Front','cpf':'111','employmentCategory':'MEI','collaboratorModel':'MEI','business':{'cnpj':'12345678000100','legalName':'Pessoa Front MEI'},'addressData':{'cep':'01001000','street':'Praça da Sé','number':'1','city':'São Paulo','state':'SP'},'health':{'hasDisease':'Não'},'bank':{'bank':'Banco','pixKey':'abc'}}],'piece_rates':[{'id':'RATE-FRONT-1','employeeId':'RH-FRONT-1','sector':'Montagem','operation':'Montar','product':'Baú','rate':3.5}],'production_entries':[{'id':'ENTRY-FRONT-1','employeeId':'RH-FRONT-1','date':'2026-07-27','sector':'Montagem','operation':'Montar','product':'Baú','quantity':4,'rate':3.5,'total':14}]}
        r=c.put('/api/v1/employees/sync/front',json=payload);assert r.status_code==200,r.text
        employees=c.get('/api/v1/employees?q=Pessoa Front').json();assert len(employees)==1
        detail=c.get(f"/api/v1/employees/{employees[0]['id']}").json();assert detail['mei']['cnpj']=='12345678000100';assert detail['address']['cep']=='01001000'
        rates=c.get(f"/api/v1/employees/piece-rates/list?employee_id={employees[0]['id']}").json();assert len(rates)==1;assert float(rates[0]['rate'])==3.5
