@echo off
chcp 65001 >nul
title Facil Pedido ERP - Homologacao
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo O sistema ainda nao foi instalado.
  echo Execute primeiro INSTALAR-WINDOWS.bat
  pause
  exit /b 1
)

if not exist "data" mkdir "data"
if not exist "storage\homologacao\uploads" mkdir "storage\homologacao\uploads"
if not exist "backup\homologacao" mkdir "backup\homologacao"

set "ENVIRONMENT=homologation"
set "APP_NAME=Facil Pedido ERP - Homologacao"
set "DATABASE_URL=sqlite:///./data/facil_pedido_homologacao.db"
set "UPLOAD_DIR=storage/homologacao/uploads"
set "BACKUP_DIR=backup/homologacao"
set "AUTH_DISABLED=true"
set "SEED_ADMIN=false"
set "AUTO_CREATE_TABLES=true"

echo Preparando banco de homologacao...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 goto erro

echo.
echo ================================================
echo  FACIL PEDIDO ERP - HOMOLOGACAO
echo  http://127.0.0.1:8000
echo ================================================
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000'"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
exit /b 0

:erro
echo.
echo [ERRO] Nao foi possivel iniciar a homologacao.
pause
exit /b 1
