from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

ROOT=Path(__file__).resolve().parents[1]

def test_front_version_is_v1813_and_production_auth_remains_required():
    config=(ROOT/'frontend'/'config.js').read_text(encoding='utf-8')
    assert '18.2.0-supabase-ready' in config
    assert 'window.FP_AUTH_REQUIRED = true' in config

def test_product_form_preloads_locations_from_authoritative_endpoint():
    html=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
    assert 'async function fpEnsureStockLocationsLoaded' in html
    assert "api._json('/api/v1/stock-locations'" in html
    assert 'if(type==="products")await fpEnsureStockLocationsLoaded({autoCreate:true});' in html
    assert '· v18.2.0' in html

def test_local_runtime_unregisters_old_service_workers():
    html=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
    assert 'navigator.serviceWorker.getRegistrations()' in html
    assert 'k.startsWith("facil-pedido-front-")' in html

def test_stock_locations_endpoint_returns_operational_defaults():
    with TestClient(app) as client:
        response=client.get('/api/v1/stock-locations')
        assert response.status_code==200
        codes={row['address_code'] for row in response.json()}
        assert {'EST-PRINCIPAL','MAT-PRIMA','EXPEDICAO','QUARENTENA'} <= codes
