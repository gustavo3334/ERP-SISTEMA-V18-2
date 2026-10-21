"""Regressão: ERP V18.2 pode não expor /stock/balance ou usar um envelope.
A interface nunca deve receber JSONResponse dentro de `balances`.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gateway import main as gateway


def _request():
    return Request({"type": "http", "method": "GET", "path": "/api/v1/inventory/balances", "query_string": b"", "headers": [(b"authorization", b"Bearer dummy-token")]})


@pytest.fixture
def allow_catalog(monkeypatch):
    monkeypatch.setattr(gateway, "_current_user", lambda request: {"role": "administrator"})
    monkeypatch.setattr(gateway, "_catalog_access", lambda user: {"read": True})


def test_stock_endpoint_unavailable_returns_array_not_response(monkeypatch, allow_catalog):
    monkeypatch.setattr(gateway, "_erp_call", lambda *args, **kwargs: (404, {"detail": "Not Found"}, {}))
    result = gateway.inventory_balances(_request())
    assert result == []
    assert isinstance(result, list)


def test_stock_endpoint_paginated_payload_becomes_array(monkeypatch, allow_catalog):
    monkeypatch.setattr(gateway, "_erp_call", lambda *args, **kwargs: (
        200,
        {"items": [{"product_id": "P1", "location_id": None, "stock": 3, "reserved_stock": 1, "available": 2}]},
        {},
    ))
    result = gateway.inventory_balances(_request())
    assert isinstance(result, list)
    assert result[0]["product_id"] == "P1"
    assert result[0]["available_quantity"] == 2


def test_stock_endpoint_unexpected_payload_is_explicit_error(monkeypatch, allow_catalog):
    monkeypatch.setattr(gateway, "_erp_call", lambda *args, **kwargs: (200, {"message": "unknown"}, {}))
    with pytest.raises(HTTPException) as ex:
        gateway.inventory_balances(_request())
    assert ex.value.status_code == 502


def test_stock_endpoint_internal_failure_is_http_error_not_json_in_array(monkeypatch, allow_catalog):
    monkeypatch.setattr(gateway, "_erp_call", lambda *args, **kwargs: (500, {"detail": "ERP Error"}, {}))
    with pytest.raises(HTTPException) as ex:
        gateway.inventory_balances(_request())
    assert ex.value.status_code == 500
