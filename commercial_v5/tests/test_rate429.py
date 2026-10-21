"""Regressões de 429: rate-limit sem repetir login/escritas e autenticação eficiente."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
from fastapi import HTTPException
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gateway import main as gateway


def make_request(method="GET"):
    return Request({"type": "http", "method": method, "path": "/api/v1/products", "query_string": b"", "headers": [(b"authorization", b"Bearer sample-token")], "state": {}})


def test_auth_me_cache_only_on_read(monkeypatch):
    count = {"calls": 0}
    def fake_json(method, path, **kwargs):
        count["calls"] += 1
        return {"role": "administrator", "id": "someone", "full_name": "Adm"}
    monkeypatch.setattr(gateway, "_erp_json", fake_json)
    gateway._user_cache.clear()
    a = gateway._current_user(make_request())
    b = gateway._current_user(make_request())
    assert a == b and count["calls"] == 1
    gateway._current_user(make_request("POST"))
    assert count["calls"] == 2
    gateway._user_cache.clear()


def test_429_non_idempotent_login_never_replayed(monkeypatch):
    calls=[]
    def fake_request(method,url,**kwargs):
        calls.append((method,url))
        return httpx.Response(429, headers={"Retry-After":"30"}, json={"detail":"Too Many Requests"})
    monkeypatch.setattr(gateway.client,"request",fake_request)
    monkeypatch.setattr(gateway,"_read_limited_until",0.0)
    status, payload, h=gateway._erp_call("POST","/auth/login",body={"email":"example@test.test","password":"secret"})
    assert status == 429 and h["Retry-After"] == "30"
    assert len(calls) == 1
    assert "secret" not in str(payload)
    response=gateway._json_response(status,payload,h)
    assert response.headers["retry-after"] == "30"
    monkeypatch.setattr(gateway,"_read_limited_until",0.0)


def test_429_get_long_retry_after_returns_with_header(monkeypatch):
    calls=[]
    def fake_request(method,url,**kwargs):
        calls.append(method)
        return httpx.Response(429,headers={"Retry-After":"45"},json={"detail":"limit"})
    monkeypatch.setattr(gateway.client,"request",fake_request)
    monkeypatch.setattr(gateway,"_read_limited_until",0.0)
    status, payload, headers=gateway._erp_call("GET","/products")
    assert status==429 and headers["Retry-After"]=="45" and len(calls)==1
    monkeypatch.setattr(gateway,"_read_limited_until",0.0)


def test_retry_after_parsing():
    assert gateway._retry_after_seconds("18") == 18
    assert gateway._retry_after_seconds("3.2") == 4
    assert gateway._retry_after_seconds("unknown") == 30


def test_read_429_does_not_block_login(monkeypatch):
    calls=[]
    def fake_request(method,url,**kwargs):
        calls.append((method,url))
        if url.endswith("/products"):
            return httpx.Response(429, json={"detail":"ratelimit"})
        return httpx.Response(200, json={"token":"fake","user":{"role":"administrator"}})
    monkeypatch.setattr(gateway.client,"request",fake_request)
    monkeypatch.setattr(gateway,"_read_limited_until",0.0)
    status, data, headers=gateway._erp_call("GET","/products")
    assert status==429 and headers["Retry-After"]=="30"
    assert headers["X-FP-429-Origin"]=="erp-response"
    status, data, _=gateway._erp_call("POST","/auth/login",body={"email":"a@b.c","password":"notreal"})
    assert status == 200 and data["token"]=="fake"
    assert len(calls)==2
    # A second product GET is short-circuited locally; its source is explicit.
    status, _, headers=gateway._erp_call("GET","/products")
    assert status==429 and headers["X-FP-429-Origin"]=="read-cooldown"
    assert len(calls)==2
    monkeypatch.setattr(gateway,"_read_limited_until",0.0)


def test_upstream_login_429_exposes_source_header(monkeypatch):
    def fake_request(method,url,**kwargs):
        return httpx.Response(429, headers={"Retry-After":"120"})
    monkeypatch.setattr(gateway.client,"request",fake_request)
    monkeypatch.setattr(gateway,"_read_limited_until",0.0)
    status, payload, meta=gateway._erp_call("POST","/auth/login",body={"email":"a@b.c","password":"notreal"})
    assert status == 429 and meta["Retry-After"] == "120"
    response=gateway._json_response(status,payload,meta)
    assert response.headers["x-fp-429-origin"] == "erp-response"
    assert response.headers["retry-after"] == "120"
    monkeypatch.setattr(gateway,"_read_limited_until",0.0)
