from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_fresh_install_has_operational_stock_locations():
    with TestClient(app) as client:
        response = client.get('/api/v1/stock-locations')
        assert response.status_code == 200
        codes = {row['address_code'] for row in response.json()}
        assert {'EST-PRINCIPAL', 'MAT-PRIMA', 'EXPEDICAO', 'QUARENTENA'} <= codes


def test_product_form_uses_real_location_id_and_empty_state_recovery():
    html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
    assert 'function fpProductLocationField(record={})' in html
    assert 'Nenhum local cadastrado' in html
    assert 'fpCreateDefaultStockLocationFromProduct(event)' in html
    assert 'name="locationId" required' in html
    assert 'locationId,location:locationRecord?' in html


def test_frontend_has_api_helpers_and_reloads_locations_when_product_form_opens():
    html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
    assert 'async function apiList(path)' in html
    assert 'async function safeApi(path,fallback=null)' in html
    assert 'apiList(\'/engenharia/locais\')' in html
    assert 'fpRefreshProductLocationField(record)' in html
    assert 'fpCreateDefaultStockLocationFromProduct(event)' in html


def test_defaults_are_added_even_when_legacy_location_exists():
    from sqlalchemy import delete, select
    from app.bootstrap import _seed_stock_locations
    from app.database import SessionLocal
    from app.models import StockLocation

    with SessionLocal() as db:
        db.execute(delete(StockLocation))
        db.add(StockLocation(name='', warehouse='', aisle='', rack='', shelf='', address_code='LEGACY-EMPTY', description='', active=True))
        db.commit()

    _seed_stock_locations()

    with SessionLocal() as db:
        codes = set(db.scalars(select(StockLocation.address_code)).all())
        assert 'LEGACY-EMPTY' in codes
        assert {'EST-PRINCIPAL', 'MAT-PRIMA', 'EXPEDICAO', 'QUARENTENA'} <= codes
