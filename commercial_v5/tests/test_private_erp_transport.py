"""Transport security and routing tests for paid ERP private network."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gateway import main


def test_default_stays_public():
    assert main._verified_erp_upstream("https://erp.example/api/v1", "", "production", True) == "https://erp.example/api/v1"


def test_private_transport_is_internal_only():
    candidate = "http://erp-sistema-v18-2-abc123:10000/api/v1"
    assert main._verified_erp_upstream("https://erp.example/api/v1", candidate, "production", True) == candidate


@pytest.mark.parametrize("value", [
    "https://erp-sistema-v18-2-abc123:10000/api/v1",
    "http://erp-sistema-v18-2.onrender.com:10000/api/v1",
    "http://127.0.0.1:10000/api/v1",
    "http://localhost:10000/api/v1",
    "http://erp-sistema-v18-2-abc123:9999/api/v1",
    "http://erp-sistema-v18-2-abc123:10000/other",
    "http://user:password@erp-sistema-v18-2-abc123:10000/api/v1",
    "http://erp-sistema-v18-2-abc123:10000/api/v1?token=abc",
])
def test_reject_unsafe_internal_addresses(value):
    with pytest.raises(RuntimeError):
        main._verified_erp_upstream("https://erp.example/api/v1", value, "production", True)


def test_private_transport_requires_render_in_prod():
    with pytest.raises(RuntimeError):
        main._verified_erp_upstream("https://erp.example/api/v1", "http://erp-abc:10000/api/v1", "production", False)


def test_real_client_targets_validated_transport(monkeypatch):
    import httpx
    got = {}
    def fake_request(method, url, **kwargs):
        got['url'] = url
        return httpx.Response(200, json={'ok': True})
    monkeypatch.setattr(main.client, 'request', fake_request)
    monkeypatch.setattr(main, 'ERP_UPSTREAM_BASE', 'http://erp-abc:10000/api/v1')
    main._erp_call('GET','/health')
    assert got['url'] == 'http://erp-abc:10000/api/v1/health'
