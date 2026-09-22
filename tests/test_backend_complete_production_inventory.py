from fastapi.testclient import TestClient
from app.main import app


def test_completed_production_enters_finished_stock():
    with TestClient(app) as c:
        p=c.post('/api/v1/products',json={'code':'FIN-001','name':'Produto Final','item_type':'Produto acabado','unit':'UN','cost':'10','technical_cost':'12','price':'25','stock':'0','reserved_stock':'0','min_stock':'0','base_stock':'0','manufacturing_enabled':True,'active':True});assert p.status_code==201,p.text;p=p.json()
        op=c.post('/api/v1/production-orders',json={'product_id':p['id'],'product_name':p['name'],'quantity':'3','production_mode':'PRODUZIR_DO_ZERO'});assert op.status_code==201,op.text
        done=c.post(f"/api/v1/production-orders/{op.json()['id']}/complete");assert done.status_code==200,done.text
        product=c.get(f"/api/v1/products/{p['id']}").json();assert float(product['stock'])==3.0
        moves=c.get(f"/api/v1/inventory/movements?product_id={p['id']}").json();assert any(x['movement_type']=='ENTRADA_PRODUCAO' for x in moves)
