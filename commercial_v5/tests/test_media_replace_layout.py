"""Integration unit tests for safe product-photo replacement.

Run from commercial_v5: python tests/test_media_replace_layout.py
No network, ERP service, or production database needed.
"""
from __future__ import annotations

import base64
import importlib.util
import io
import os
import sys
import tempfile
from pathlib import Path

from fastapi import HTTPException
from PIL import Image
from starlette.requests import Request


def run_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        previous = os.environ.get("CATALOG_DATABASE_URL")
        try:
            os.environ["CATALOG_DATABASE_URL"] = "sqlite:///" + str(Path(tmp) / "test.db").replace("\\", "/")
            os.environ["COMBINED_DEPLOYMENT"] = "false"
            gateway_file = Path(__file__).resolve().parents[1] / "gateway" / "main.py"
            spec = importlib.util.spec_from_file_location("photo_replace_layout_test_module", gateway_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            module.Base.metadata.create_all(module.engine)
            module._require_catalog = lambda request, scope: {"email": "editor@local.test", "full_name": "Editor"}
            module._erp_call = lambda *args, **kwargs: (200, {}, {})
            module._service_token = lambda: "test-token"

            bitmap = Image.new("RGB", (32, 32), "#0d6efd")
            image_bytes = io.BytesIO()
            bitmap.save(image_bytes, format="PNG")
            data_url = "data:image/png;base64," + base64.b64encode(image_bytes.getvalue()).decode("ascii")
            request = Request({
                "type": "http", "method": "POST", "path": "/api/v1/media/replace", "headers": [],
                "scheme": "http", "server": ("testserver", 80), "root_path": "", "app": module.app,
            })
            with module.SessionLocal() as session:
                media_id = "00000000-0000-0000-0000-000000000001"
                old_url = "http://oldservice.onrender.com/api/v1/media/" + media_id
                session.add(module.ProductMedia(
                    id=media_id, product_id="P1", filename="old.jpg", content_type="image/png", content=b"old bytes",
                ))
                session.add(module.CatalogState(
                    key=module.CATALOG_KEY,
                    payload={"media": {"P1": {"photos": [old_url, "https://example.org/legacy.jpg"]}}},
                    revision=1,
                ))
                session.commit()
                response = module.media_replace(
                    module.MediaReplaceInput(product_id="P1", index=0, filename="new.png", data_url=data_url),
                    request, session,
                )
                assert response["id"] == media_id, "Existing stored media ID should be reused"
                assert "?v=" in response["url"], "Replacement must cache-bust across browsers"
                assert session.get(module.ProductMedia, media_id).content != b"old bytes"
                photos = session.get(module.CatalogState, module.CATALOG_KEY).payload["media"]["P1"]["photos"]
                assert len(photos) == 2 and photos[0] == response["url"]
                assert "?v=" in module._catalog_with_persisted_media(session, request)["payload"]["media"]["P1"]["photos"][0]

                legacy = module.media_replace(
                    module.MediaReplaceInput(product_id="P1", index=1, filename="converted.png", data_url=data_url),
                    request, session,
                )
                assert legacy["id"] != media_id
                assert session.get(module.CatalogState, module.CATALOG_KEY).payload["media"]["P1"]["photos"][1] == legacy["url"]
                try:
                    module.media_replace(
                        module.MediaReplaceInput(product_id="P1", index=5, filename="bad.png", data_url=data_url),
                        request, session,
                    )
                except HTTPException as ex:
                    assert ex.status_code == 409
                else:
                    raise AssertionError("Invalid gallery position must be rejected")
                print("PASS: troca segura, ordem, atualização de cache, mídia legada e validação de índice")
            module.engine.dispose()
        finally:
            if previous is None:
                os.environ.pop("CATALOG_DATABASE_URL", None)
            else:
                os.environ["CATALOG_DATABASE_URL"] = previous


if __name__ == "__main__":
    run_test()
