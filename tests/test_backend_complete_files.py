from fastapi.testclient import TestClient
from app.main import app

def test_document_upload():
    with TestClient(app) as c:
        e=c.post('/api/v1/employees',json={'legacy_id':'COL-DOC-1','full_name':'Documento Teste'}).json()
        u=c.post('/api/v1/files/employee-document',data={'employee_id':e['id'],'document_type':'RG'},files={'file':('rg.pdf',b'%PDF-1.4 teste','application/pdf')});assert u.status_code==200,u.text
        d=c.get(f"/api/v1/files/{u.json()['id']}/download");assert d.status_code==200;assert d.content.startswith(b'%PDF')
