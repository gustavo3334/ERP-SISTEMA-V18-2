from datetime import date
from fastapi.testclient import TestClient
from app.main import app


def test_employee_full_crud():
    payload={"legacy_id":"COL-RH-001","full_name":"Colaborador Teste","employment_category":"Sem registro","start_date":date.today().isoformat(),"cpf":"00000000000","position":"Montador","sector":"Montagem","salary":"2500.00","address":{"cep":"00000000","street":"Rua Teste","number":"10","city":"São Paulo","state":"SP","residence_type":"Apartamento","apartment":"12","block":"B"},"contacts":[{"contact_type":"Emergência","name":"Contato","relationship":"Irmão","phone":"11888888888","priority":1}],"health":{"continuous_medication":True,"medication":"Medicamento de teste"},"dependents":[{"legacy_id":"DEP-1","name":"Filho Teste","birth_date":"2020-01-01","relationship":"Filho(a)","alimony":{"active":True,"agreement_type":"Judicial","fixed_amount":"300.00"}}],"bank_accounts":[{"bank":"Banco Teste","agency":"0001","account":"12345","pix_type":"CPF","pix_key":"00000000000","portability":True,"destination_bank":"Outro Banco"}],"bonuses":[{"legacy_id":"BON-1","bonus_type":"Produtividade","amount":"150.00","recurring":True}],"transport_plan":{"company_address":"Empresa","employee_address":"Casa","working_days":22,"legs":[{"transport_type":"Ônibus","line":"001","fare":"5.00","uses_per_day":"2"}]}}
    with TestClient(app) as client:
        r=client.post('/api/v1/employees',json=payload);assert r.status_code==201,r.text;d=r.json();assert d['address']['apartment']=='12';assert d['health']['continuous_medication'] is True;assert d['dependents'][0]['alimony']['agreement_type']=='Judicial';assert float(d['transport_plan']['monthly_cost'])==220.0
        r2=client.get(f"/api/v1/employees/{d['id']}");assert r2.status_code==200;assert r2.json()['bank_accounts'][0]['portability'] is True


def test_piece_rate_payroll():
    with TestClient(app) as c:
        e=c.post('/api/v1/employees',json={'legacy_id':'COL-PROD-001','full_name':'Produtor Teste','salary':'2000'}).json()
        r=c.post('/api/v1/employees/piece-rates',json={'employee_id':e['id'],'sector':'Tapeçaria','operation':'Tapeçar','product_name':'Baú 138','rate':'2.50'});assert r.status_code==200,r.text
        x=c.post('/api/v1/employees/production-entries',json={'legacy_id':'ENTRY-001','employee_id':e['id'],'entry_date':date.today().isoformat(),'sector':'Tapeçaria','operation':'Tapeçar','product_name':'Baú 138','quantity':'10'});assert x.status_code==200,x.text;assert float(x.json()['total'])==25.0
        competence=date.today().strftime('%Y-%m');p=c.post(f"/api/v1/employees/{e['id']}/payroll/preview",json={'competence':competence});assert p.status_code==200,p.text;assert float(p.json()['piece_production'])==25.0
