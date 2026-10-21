@echo off
cd /d "%~dp0"
set MOCK_ERP_DATABASE_URL=sqlite:///./mock_erp.db
"%~dp0..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
