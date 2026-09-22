from fastapi.testclient import TestClient
from app.main import app

def prod(c,code):
    r=c.post('/api/v1/products',json={'code':code,'name':code,'item_type':'Produto acabado','unit':'UN','cost':'10','technical_cost':'10','price':'25','stock':'0','reserved_stock':'0','min_stock':'0','base_stock':'0','manufacturing_enabled':False,'active':True});assert r.status_code==201,r.text;return r.json()

def test_purchase_and_sales_flow():
    with TestClient(app) as c:
        p=prod(c,'FLOW-001')
        po=c.post('/api/v1/purchase-orders',json={'items':[{'product_id':p['id'],'quantity':'10','unit_cost':'8'}]});assert po.status_code==201,po.text;item=po.json()['items'][0]
        rr=c.post(f"/api/v1/purchase-orders/{po.json()['id']}/receive",json={'items':[{'item_id':item['id'],'quantity':'10'}]});assert rr.status_code==200,rr.text
        assert c.get(f"/api/v1/products/{p['id']}").json()['stock']=='10.000'
        so=c.post('/api/v1/sales-orders',json={'client_name':'Cliente','delivery_address':'Rua 1','items':[{'product_id':p['id'],'quantity':'2','unit_price':'25'}]});assert so.status_code==201,so.text;oid=so.json()['id']
        cf=c.post(f'/api/v1/sales-orders/{oid}/confirm',json={'auto_create_production':True,'create_receivable':True});assert cf.status_code==200,cf.text
        sh=c.post(f'/api/v1/sales-orders/{oid}/ship');assert sh.status_code==200,sh.text
        assert c.get(f"/api/v1/products/{p['id']}").json()['stock']=='8.000'
