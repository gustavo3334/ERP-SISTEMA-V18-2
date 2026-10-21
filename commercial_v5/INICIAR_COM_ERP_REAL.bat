@echo off
setlocal
cd /d "%~dp0"
if not exist ".env.real" (
  echo ========================================================
  echo ARQUIVO .env.real NAO ENCONTRADO
  echo ========================================================
  echo Copie .env.real.example para .env.real e preencha:
  echo - ERP_API_BASE
  echo - ERP_SERVICE_EMAIL
  echo - ERP_SERVICE_PASSWORD
  echo - CATALOG_DATABASE_URL ^(a mesma base Neon/PostgreSQL do ERP^)
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" call INSTALAR.bat
start "Facil Pedido - Gateway ERP Real" cmd /k "cd /d \"%~dp0gateway\" && \"%~dp0.venv\Scripts\python.exe\" run_real.py"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:8010/"
echo Gateway iniciado em http://127.0.0.1:8010/api/v1
pause
