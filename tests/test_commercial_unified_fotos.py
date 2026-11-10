"""QA isolada do Comercial montado em /comercial. Não acessa Render nem ERP de produção.
Execute: python -m pytest -q tests/test_commercial_unified_fotos.py
"""
from __future__ import annotations
import base64
import io
import json
import os
import subprocess
import sys
from pathlib import Path


def test_unified_routes_upload_and_edit(monkeypatch, tmp_path):
    monkeypatch.setenv('COMBINED_DEPLOYMENT','true')
    monkeypatch.setenv('PORT','10000')
    monkeypatch.setenv('ENVIRONMENT','development')
    monkeypatch.setenv('AUTO_CREATE_TABLES','false')
    monkeypatch.setenv('CATALOG_DATABASE_URL','sqlite:///'+str(tmp_path/'catalog.db'))
    monkeypatch.setenv('DATABASE_URL','sqlite:///'+str(tmp_path/'erp.db'))
    # Tests are run in a fresh interpreter: import startup must follow isolated env vars.
    from combined_app import app
    from gateway import main as gateway
    from fastapi.testclient import TestClient
    from PIL import Image
    gateway.Base.metadata.create_all(gateway.engine)
    gateway._require_catalog=lambda request,action: {'role':'administrator','email':'admin@local.test','permissions':['*']}
    gateway._current_user=lambda request: {'role':'administrator','email':'admin@local.test','permissions':['*']}
    gateway._service_token=lambda: 'test-token'
    gateway._erp_call=lambda *a,**k:(200, {'id':'P-01'}, {})
    client=TestClient(app,base_url="https://testserver")
    for path,mime in [
        ('/comercial/', 'text/html'),
        ('/comercial/pv-assets/cover-005.jpg','image/jpeg'),
        ('/comercial/pv-assets/pv_pagina_005_principal.webp','image/webp'),
        ('/comercial/assets/facil-pedido-marca.png','image/png'),
    ]:
        resp=client.get(path)
        assert resp.status_code==200, (path,resp.text[:200])
        assert resp.headers['content-type'].startswith(mime)
    html=client.get('/comercial/').text
    assert 'VERSION: "5.3.0-unificado-studio-render"' in html
    assert 'location.pathname.startsWith("/comercial")' in html
    assert '/media/replace' in html
    assert '/comercial/api/v1' in html
    assert client.get('/comercial/api/v1/porto-velho/referencias').json()['rows']
    b=io.BytesIO(); Image.new('RGB',(55,55),(255,150,70)).save(b,format='PNG')
    data_url='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
    api='/comercial/api/v1'
    before=client.get(api+'/catalog-management/state').json()
    assert before['revision']==0
    created=client.post(api+'/media',json={'product_id':'P-01','filename':'foto.png','data_url':data_url})
    assert created.status_code==200,created.text
    obj=created.json(); assert obj['revision']==1
    assert '/comercial/api/v1/media/' in obj['url']
    stored=client.get(api+'/catalog-management/state').json()
    assert stored['payload']['media']['P-01']['photos']==[obj['url']]
    payload={'media':stored['payload']['media'],'presentation':{'P-01':{'title':'Móvel alterado','description':'Descrição editável','published':True}}}
    saved=client.put(api+'/catalog-management/state',json={'base_revision':1,'payload':payload})
    assert saved.status_code==200,saved.text
    rev=saved.json()['revision']
    changed=client.post(api+'/media/replace',json={'product_id':'P-01','index':0,'filename':'nova.png','data_url':data_url})
    assert changed.status_code==200,changed.text
    assert changed.json()['revision']==rev+1
    new=client.get(api+'/catalog-management/state').json()
    assert new['payload']['presentation']['P-01']['description']=='Descrição editável'
    assert new['payload']['media']['P-01']['photos'][0]==changed.json()['url']
    assert client.get(api+'/media/'+obj['id']).status_code==200
    # Media bytes persist through a new independent database session.
    with gateway.SessionLocal() as session:
        assert session.get(gateway.ProductMedia,obj['id']) is not None
    deleted=client.delete(api+'/media/'+obj['id'])
    assert deleted.status_code==204
    assert not client.get(api+'/catalog-management/state').json()['payload']['media']['P-01']['photos']
    assert client.get(api+'/media/'+obj['id']).status_code==404
    gateway.engine.dispose()
