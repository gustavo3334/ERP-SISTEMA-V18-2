from fastapi.testclient import TestClient
from app.main import app

def create_product(c,code):
    r=c.post('/api/v1/products',json={'code':code,'name':code,'item_type':'Matéria-prima','unit':'UN','cost':'10','technical_cost':'0','price':'20','stock':'0','reserved_stock':'0','min_stock':'0','base_stock':'0','manufacturing_enabled':False,'active':True});assert r.status_code==201,r.text;return r.json()

def test_stock_movement_and_reservation():
    with TestClient(app) as c:
        p=create_product(c,'EST-COMP-001');m=c.post('/api/v1/inventory/movements',json={'product_id':p['id'],'movement_type':'AJUSTE_ENTRADA','quantity':'20','unit_cost':'10'});assert m.status_code==200,m.text
        r=c.post('/api/v1/inventory/reserve',json={'product_id':p['id'],'quantity':'5'});assert r.status_code==200,r.text
        b=c.get(f"/api/v1/inventory/balances?product_id={p['id']}").json()[0];assert float(b['quantity'])==20.0;assert float(b['available_quantity'])==15.0
