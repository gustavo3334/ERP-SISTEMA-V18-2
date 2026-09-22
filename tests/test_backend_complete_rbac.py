from fastapi.testclient import TestClient
from app.main import app

def test_profiles_dev_mode():
    with TestClient(app) as c:
        r=c.post('/api/v1/access-control/profiles',json={'name':'RH Teste','permissions':['rh.read','rh.write']});assert r.status_code==200,r.text
        assert any(x['name']=='RH Teste' for x in c.get('/api/v1/access-control/profiles').json())
