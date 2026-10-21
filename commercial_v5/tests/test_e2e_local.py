"""Teste de integração V5 sem servidores externos, em bancos temporários.
Uso: python tests/test_e2e_local.py
"""
import base64
import io
from PIL import Image
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "mock_erp"
GATE = ROOT / "gateway"


def check() -> None:
    with tempfile.TemporaryDirectory(prefix="facilpedido_test_") as folder:
        root = Path(folder)
        mock_env = {**os.environ, "MOCK_ERP_DATABASE_URL": f"sqlite:///{root/'mock.db'}"}
        gate_env = {**os.environ, "ERP_API_BASE": "http://127.0.0.1:8180/api/v1", "CATALOG_DATABASE_URL": f"sqlite:///{root/'catalog.db'}", "ERP_SERVICE_EMAIL": "admin@facilpedido.local", "ERP_SERVICE_PASSWORD": "TroqueEstaSenha123!"}
        commands = [
            subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8180", "--log-level", "error"], cwd=MOCK, env=mock_env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE),
        ]
        try:
            cli = httpx.Client(timeout=15)
            for _ in range(100):
                try:
                    if cli.get("http://127.0.0.1:8180/api/v1/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.08)
            else:
                raise AssertionError("ERP de teste não iniciou")
            commands.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8181", "--log-level", "error"], cwd=GATE, env=gate_env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE))
            api = "http://127.0.0.1:8181/api/v1"
            for _ in range(100):
                try:
                    if cli.get(api+"/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.08)
            else:
                raise AssertionError("Gateway não iniciou")

            def req(method, path, headers=None, data=None, status=200):
                resp = cli.request(method, api+path, headers=headers or {}, json=data)
                if resp.status_code not in ((200,201) if status==201 else (status,)):
                    raise AssertionError(f"{method} {path}: esperado {status}, recebido {resp.status_code}\n{resp.text[:1400]}")
                return resp.json() if resp.content else None

            admin = req("POST", "/auth/login", data={"email":"admin@facilpedido.local","password":"TroqueEstaSenha123!"})
            rh = req("POST", "/auth/login", data={"email":"rh@facilpedido.local","password":"RHcatalogo123!"})
            sales = req("POST", "/auth/login", data={"email":"vendas@facilpedido.local","password":"Vendas123!"})
            AH = {"Authorization": "Bearer " + admin["token"]}
            RH = {"Authorization": "Bearer " + rh["token"]}
            SH = {"Authorization": "Bearer " + sales["token"]}
            assert "catalog.write" in rh["permissions"]
            products = req("GET", "/catalog-management/products", headers=RH)
            assert products["products"] and "cost" not in products["products"][0]
            assert "cost" not in products["variants"][0] if products["variants"] else True
            pid = products["products"][0]["id"]
            # RH não pode alterar dados técnicos nem elevar estoque.
            req("POST", "/products", headers=RH, data={"code":"INDEVIDO","name":"Inválido"}, status=403)
            req("POST", "/inventory/balances", headers=RH, data={"product_id":pid,"quantity":999}, status=403)
            req("GET", "/integration/snapshot", headers=RH, status=403)
            req("GET", "/sales-orders", headers=RH, status=403)
            stock = req("GET", "/inventory/balances", headers=RH)
            assert stock and stock[0]["product_id"] == pid
            prod = req("POST", "/products", headers=AH, data={"code":"SOF-NEW","name":"Sofá Milano","price":3590,"cost":1400,"stock":2,"active":True}, status=201)
            assert prod["name"] == "Sofá Milano"
            variant = req("POST", "/product-variants", headers=AH, data={"product_id":prod["id"],"sku":"SOF-NEW-CINZA","color":"Cinza","size":"3 lugares","stock":2,"price":3790}, status=201)
            assert variant["sku"] == "SOF-NEW-CINZA"
            assert "cost" not in req("GET", "/products", headers=SH)[0]
            assert "cost" not in req("GET", "/products/"+prod["id"], headers=RH)
            assert "cost" not in req("GET", "/product-variants", headers=RH)[0]
            assert "cost" in req("GET", "/products/"+prod["id"], headers=AH)
            # RH pode adicionar foto, publicar e não pode alterar 'settings' ou finanças.
            image_io = io.BytesIO()
            Image.new("RGB", (32, 32), "#c9b6a5").save(image_io, format="PNG")
            img = image_io.getvalue()
            photo = req("POST", "/media", headers=RH, data={"product_id":prod["id"],"filename":"sofa.png","data_url":"data:image/png;base64,"+base64.b64encode(img).decode()})
            photo_response = cli.get(api+photo["path"])
            assert photo_response.status_code == 200 and photo_response.headers["content-type"].startswith("image/jpeg")
            assert len(photo_response.content) > 100
            status = req("GET", "/catalog-management/state", headers=RH)
            payload = {"presentation": {prod["id"]: {"title":"Sofá Milano Premium","published":True,"description":"Sofá confortável."}},"media":{prod["id"]:{"photos":[api+photo["path"]],"variantPhotos":{}}},"settings":{"minimumMargin":0},"operations":{"receivables":[{"amount":90000}]}}
            req("PUT", "/catalog-management/state", headers=RH, data={"payload":payload,"base_revision":status["revision"]})
            rv = req("GET", "/catalog-management/state", headers=RH)
            assert rv["payload"].get("settings",{}).get("minimumMargin") is None
            assert rv["payload"].get("operations") is None
            assert rv["payload"]["presentation"][prod["id"]]["title"] == "Sofá Milano Premium"
            req("PUT", "/catalog-management/state", headers=RH, data={"payload":payload,"base_revision":0}, status=409)
            req("PUT", "/catalog-management/state", headers=RH, data={"payload":payload}, status=428)
            published = req("GET", "/public/catalog")["products"]
            assert any(x["id"] == prod["id"] and x["cover"] == api+photo["path"] for x in published)
            assert not any("cost" in x for x in published)
            # Segurança: upload não aceita MIME falso, produto inexistente, nem fotos excessivamente grandes.
            req("POST", "/media", headers=RH, data={"product_id": prod["id"], "filename":"falso.png", "data_url": "data:image/png;base64,"+base64.b64encode(b"nao e imagem").decode()}, status=400)
            req("POST", "/media", headers=RH, data={"product_id": "produto-que-nao-existe", "filename":"foto.png", "data_url": "data:image/png;base64,"+base64.b64encode(img).decode()}, status=404)
            req("GET", "/client-management/1/product-price/2", status=401)
            req("GET", "/client-management/1/product-price/2", headers=RH, status=404)
            req("POST", "/sales-orders", headers=SH, data={"items":[{"quantity":-2,"unit_price":1000}]}, status=422)
            # HTML amarelo e vitrine servidos pelo mesmo domínio para evitar CORS desnecessário.
            assert cli.get("http://127.0.0.1:8181/").status_code == 200
            assert "Fácil Pedido" in cli.get("http://127.0.0.1:8181/").text
            assert cli.get("http://127.0.0.1:8181/site-demo.html").status_code == 200
            assert cli.get(api+"/health/live").json()["status"] == "alive"
            for _ in range(11):
                req("POST", "/media", headers=RH, data={"product_id":prod["id"],"filename":"extra.png","data_url":"data:image/png;base64,"+base64.b64encode(img).decode()})
            req("POST", "/media", headers=RH, data={"product_id":prod["id"],"filename":"extra.png","data_url":"data:image/png;base64,"+base64.b64encode(img).decode()}, status=409)
            # Cliente e pedido financeiro/produção usam ERP real de teste.
            client = req("POST", "/clients", headers=SH, data={"name":"Cliente Teste","phone":"11999999999"}, status=201)
            order = req("POST", "/sales-orders", headers=SH, data={"client_id":client["id"],"client_name":client["name"],"payment_method":"PIX","delivery_address":"Rua Teste, 123","discount":0,"freight":50,"items":[{"product_id":pid,"description":"Sofá de teste","quantity":2,"unit_price":2500,"discount_percent":0}]},status=201)
            # Um vendedor não pode forjar um pedido como confirmado usando PUT.
            edited = req("PUT", f"/sales-orders/{order['id']}", headers=SH, data={"status":"Confirmado","items":order["items"]})
            assert edited["status"] == "Rascunho"
            confirmed = req("POST", f"/sales-orders/{order['id']}/confirm", headers=SH, data={"auto_create_production":True,"create_receivable":True})
            assert confirmed["order"]["status"] in {"Confirmado","Integração parcial"}
            req("PUT", f"/sales-orders/{order['id']}", headers=SH, data={"items":order["items"]}, status=409)
            req("DELETE", f"/sales-orders/{order['id']}", headers=AH, status=409)
            if confirmed["order"]["status"] == "Integração parcial":
                req("POST", f"/sales-orders/{order['id']}/confirm", headers=SH, data={}, status=409)
            # Vendas pode acompanhar seus pedidos, mas não editar catálogo técnico.
            assert isinstance(req("GET", "/sales-orders", headers=SH), list)
            req("POST", "/products", headers=SH, data={"name":"Não autorizado","code":"NO"}, status=403)
            snap = req("GET", "/integration/snapshot", headers=AH)
            assert any(x["id"] == prod["id"] for x in snap["products"])
            print("PASSOU: logins, produtos, RH sem custos, RBAC, upload, publicação, site, variações, vendas, pedido, estoque e snapshot")
        finally:
            for proc in reversed(commands):
                proc.terminate()
            for proc in reversed(commands):
                try:
                    _, err = proc.communicate(timeout=5)
                    if proc.returncode not in (0, -15, None):
                        print(f"Servidor retorno {proc.returncode}: {err.decode(errors='replace')[-900:]}")
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    check()
