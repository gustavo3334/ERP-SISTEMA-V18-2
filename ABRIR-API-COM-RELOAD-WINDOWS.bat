@echo off
chcp 65001 >nul
title Facil Pedido ERP - Desenvolvimento
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  call INSTALAR-WINDOWS.bat
  if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m alembic upgrade head
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000/docs'"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
