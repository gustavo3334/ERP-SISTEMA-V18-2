from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend"
PUBLIC = ROOT / "public"


def _html() -> str:
    return (FRONT / "index.html").read_text(encoding="utf-8")


def test_front_and_public_runtime_files_match():
    names = [
        "index.html",
        "config.js",
        "api-bridge.js",
        "preproduction.js",
        "stabilization-v13.js",
        "stabilization-v14.js",
        "stabilization-v15.js",
        "sw.js",
    ]
    for name in names:
        assert (FRONT / name).read_bytes() == (PUBLIC / name).read_bytes(), name


def test_html_has_no_duplicate_ids():
    soup = BeautifulSoup(_html(), "html.parser")
    ids = [tag.get("id") for tag in soup.find_all(attrs={"id": True})]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    assert duplicates == []


def test_all_inline_handler_functions_exist():
    html = _html()
    js = html + "\n" + "\n".join(
        p.read_text(encoding="utf-8") for p in FRONT.glob("*.js")
    )
    defined = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", js))
    defined |= set(re.findall(r"(?:window\.)?([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?function\s*\(", js))
    defined |= set(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(?[^=;]*?=>", js))

    calls: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        for attr in ("onclick", "onchange", "oninput", "onsubmit", "onblur", "onkeydown"):
            value = tag.get(attr)
            if not value:
                continue
            calls |= set(re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", value))

    browser_builtins = {
        "alert", "confirm", "prompt", "setTimeout", "clearTimeout", "parseInt", "parseFloat",
        "Number", "String", "Boolean", "Date", "JSON", "encodeURIComponent", "decodeURIComponent",
        "toggle",
    }
    unresolved = sorted(name for name in calls if name not in defined and name not in browser_builtins)
    assert unresolved == []


def test_persistence_engine_captures_extended_state_and_does_not_seed_demo_purchase_rows():
    html = _html()
    for marker in [
        "state.rhEmployees = clone(rhEmployees)",
        "state.rhPieceRates = clone(rhPieceRates)",
        "state.rhProductionEntries = clone(rhProductionEntries)",
        "state.sensitiveAudit = clone(sensitiveAudit)",
        "state.purchaseFollowupData = clone(purchaseFollowupData)",
        "state.frontendWorkflowStore = clone(frontendMockStore)",
        'const SERVER_STATE_KEY = "sistema-completo"',
        "base_revision: serverRevision",
    ]:
        assert marker in html
    assert "const purchaseFollowupData=[];" in html
    assert "LUCENDI PRIME MOVEIS" not in html


def test_hydration_preserves_extended_product_and_supplier_fields():
    html = _html()
    for marker in [
        "const localSuppliers=[...(enterpriseData.suppliers||[])]",
        "const localProducts=[...(enterpriseData.products||[])]",
        '["subtitle","subcategory","origin","salesChannel","assemblyCost","barcode","hideSupplierStock","displayInFacilPedido","soldMode","balanceQuantity","responsible","productStockLabel","productStockRef","productStockName","photo","expiry","notes"]',
        "merged[key]=old[key]",
    ]:
        assert marker in html


def test_modal_overlay_bug_is_not_present():
    js = (FRONT / "stabilization-v14.js").read_text(encoding="utf-8")
    assert "getElementById('modal').classList.add('show')" not in js
    assert "getElementById('modalOverlay').classList.add('show')" in js


def test_purchase_order_can_be_updated_and_remains_updated():
    with TestClient(app) as client:
        product = client.post(
            "/api/v1/products",
            json={
                "code": "AUD-PROD-001",
                "name": "Produto auditoria",
                "item_type": "Produto acabado",
                "unit": "UN",
                "cost": "10",
                "technical_cost": "10",
                "price": "25",
                "stock": "0",
                "reserved_stock": "0",
                "min_stock": "0",
                "base_stock": "0",
                "manufacturing_enabled": False,
                "active": True,
            },
        )
        assert product.status_code == 201, product.text

        order = client.post(
            "/api/v1/purchase-orders",
            json={
                "notes": "antes",
                "freight": "0",
                "items": [{"product_id": product.json()["id"], "quantity": "2", "unit_cost": "8"}],
            },
        )
        assert order.status_code == 201, order.text
        order_id = order.json()["id"]

        updated = client.put(
            f"/api/v1/purchase-orders/{order_id}",
            json={"notes": "depois", "freight": "12.50", "status": "Em cotação"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["notes"] == "depois"
        assert float(updated.json()["freight"]) == 12.50
        assert updated.json()["status"] == "Em cotação"

        loaded = client.get(f"/api/v1/purchase-orders/{order_id}")
        assert loaded.status_code == 200
        assert loaded.json()["notes"] == "depois"
        assert float(loaded.json()["freight"]) == 12.50
        assert loaded.json()["status"] == "Em cotação"


def test_quote_create_requires_sales_write_marker():
    source = (ROOT / "app" / "routers" / "quotes.py").read_text(encoding="utf-8")
    assert '@router.post("", response_model=QuoteRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sales.write"))])' in source


def test_fastapi_version_matches_front_release():
    assert 'version="18.2.0"' in (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '18.2.0-supabase-ready' in (FRONT / "config.js").read_text(encoding="utf-8")


def test_enterprise_relational_delete_guard_prevents_deleted_records_from_returning():
    html = _html()
    assert 'id="fpSeniorRelationalDeleteGuard"' in html
    assert 'await api.delete(`/${type}/${serverId}`)' in html
    assert 'await window.fpDeleteClientRelational?.(id)' in html
    assert 'Registro excluído do sistema' in html


def test_product_sync_resolves_backend_foreign_keys_instead_of_local_ids():
    js = (FRONT / "stabilization-v13.js").read_text(encoding="utf-8")
    assert "categoryRecord?.id||null" in js
    assert "supplierRecord?._serverId||supplierRecord?.id||null" in js
    assert "locationRecord?.id||null" in js


def test_legacy_engineering_layer_no_longer_overrides_real_backend_crud():
    html = _html()
    assert "async function saveEngineeringForm()" in html
    assert "api.put(`${base}/${id}`,payload)" in html
    assert "api.post(base,payload)" in html
    legacy_start = html.index("/* Engenharia: salvar/excluir agora altera os arrays locais. */")
    legacy_end = html.index("/* Enterprise: mantém CRUD nativo", legacy_start)
    legacy = html[legacy_start:legacy_end]
    assert "const saveEngineeringFormLegacyV106=async function()" in legacy
    assert "const deleteEngineeringRecordLegacyV106=function" in legacy
    assert "\nsaveEngineeringForm=async function" not in legacy
    assert "\ndeleteEngineeringRecord=function" not in legacy


def test_engineering_supplier_select_uses_relational_server_id():
    html = _html()
    assert "supplierOptions=enterpriseData.suppliers.map(x=>`${x._serverId||x.id} | ${x.legalName}`)" in html
    assert "String(x._serverId||x.id)===String(id)" in html


def test_relational_supplier_product_engineering_flow_roundtrip():
    with TestClient(app) as client:
        supplier = client.post("/api/v1/suppliers", json={"legal_name": "Fornecedor Audit", "trade_name": "Audit"})
        assert supplier.status_code == 201, supplier.text
        sid = supplier.json()["id"]

        category = client.post("/api/v1/categories", json={"name": "Categoria Audit", "item_type": "Produto acabado"})
        assert category.status_code == 201, category.text
        cid = category.json()["id"]

        location = client.post("/api/v1/stock-locations", json={"name": "Estoque Audit", "warehouse": "Principal", "address_code": "AUD-LOC-001"})
        assert location.status_code == 201, location.text
        lid = location.json()["id"]

        product = client.post("/api/v1/products", json={
            "code": "AUD-REL-001", "name": "Produto Relacional Audit", "item_type": "Produto acabado",
            "category_id": cid, "supplier_id": sid, "location_id": lid, "unit": "UN",
            "cost": "10", "technical_cost": "10", "price": "20", "stock": "5",
            "reserved_stock": "0", "min_stock": "1", "base_stock": "1", "manufacturing_enabled": False, "active": True,
        })
        assert product.status_code == 201, product.text
        pid = product.json()["id"]
        loaded = client.get(f"/api/v1/products/{pid}")
        assert loaded.status_code == 200
        assert loaded.json()["supplier_id"] == sid
        assert loaded.json()["category_id"] == cid
        assert loaded.json()["location_id"] == lid

        variant = client.post("/api/v1/product-variants", json={
            "product_id": pid, "sku": "AUD-SKU-001", "barcode": "7890000000001",
            "color": "Preto", "size": "138", "supplier_id": sid, "location_id": lid,
            "stock": "3", "reserved_stock": "0", "min_stock": "1", "cost": "10", "price": "20",
        })
        assert variant.status_code == 201, variant.text
        vid = variant.json()["id"]
        assert client.get(f"/api/v1/product-variants/{vid}").json()["supplier_id"] == sid

        assert client.delete(f"/api/v1/product-variants/{vid}").status_code == 204
        assert client.delete(f"/api/v1/products/{pid}").status_code == 204
        assert client.delete(f"/api/v1/categories/{cid}").status_code == 204
        assert client.delete(f"/api/v1/stock-locations/{lid}").status_code == 204
        assert client.delete(f"/api/v1/suppliers/{sid}").status_code == 204
