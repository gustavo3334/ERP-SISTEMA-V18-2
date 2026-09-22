@echo off
chcp 65001 >nul
title Facil Pedido ERP - Backend
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo O backend ainda nao foi instalado.
  call INSTALAR-WINDOWS.bat
  if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"

if not exist ".env" copy ".env.example" ".env" >nul
if not exist "data" mkdir "data"

python -m alembic upgrade head
if errorlevel 1 (
  echo.
  echo [ERRO] Nao foi possivel atualizar o banco.
  pause
  exit /b 1
)

python -m app.seed
if errorlevel 1 (
  echo.
  echo [ERRO] Nao foi possivel preparar o sistema.
  pause
  exit /b 1
)

echo.
echo ==========================================================
echo  Facil Pedido ERP
echo  Sistema: http://127.0.0.1:8000
echo  API:     http://127.0.0.1:8000/api/v1
echo  Docs:    http://127.0.0.1:8000/docs
echo ==========================================================
echo.
echo Nao feche esta janela enquanto estiver usando o sistema.
echo Para encerrar, pressione CTRL + C.
echo.

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000'"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo O servidor foi encerrado.
pause
