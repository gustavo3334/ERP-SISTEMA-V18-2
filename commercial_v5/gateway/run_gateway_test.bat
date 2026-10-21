@echo off
cd /d "%~dp0"
set ERP_API_BASE=http://127.0.0.1:8000/api/v1
set ERP_SERVICE_EMAIL=admin@facilpedido.local
set ERP_SERVICE_PASSWORD=TroqueEstaSenha123!
set CATALOG_DATABASE_URL=sqlite:///./facil_pedido_catalogo.db
set CORS_ORIGINS=*
"%~dp0..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8010
