@echo off
chcp 65001 >nul
title Facil Pedido ERP - Resetar banco local
cd /d "%~dp0"

echo ATENCAO: isso apaga o banco SQLite local.
set /p CONFIRMA=Digite APAGAR para continuar: 
if /I not "%CONFIRMA%"=="APAGAR" (
  echo Operacao cancelada.
  pause
  exit /b 0
)

if exist "data\facil_pedido.db" (
  copy "data\facil_pedido.db" "data\backup-antes-reset.db" >nul
  del "data\facil_pedido.db"
)

call ".venv\Scripts\activate.bat"
python -m alembic upgrade head
python -m app.seed

echo Banco local recriado.
pause
