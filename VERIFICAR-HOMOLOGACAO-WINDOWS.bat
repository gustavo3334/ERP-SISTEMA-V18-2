@echo off
chcp 65001 >nul
title Facil Pedido ERP - Verificacao da Homologacao
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  call INSTALAR-WINDOWS.bat
  if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"

rem Testes usam banco temporario e nao mexem no banco de homologacao.
set "DATABASE_URL=sqlite:///./data/test_facil_pedido.db"
set "AUTH_DISABLED=true"
set "AUTO_CREATE_TABLES=true"
set "UPLOAD_DIR=./data/test_uploads"
set "BACKUP_DIR=./data/test_backups"

python -m pytest -q

if errorlevel 1 (
  echo.
  echo [ERRO] Algum teste falhou.
  echo Envie uma captura desta janela antes de liberar a versao.
  echo.
  pause
  exit /b 1
)

echo.
echo ==========================================================
echo  VERIFICACAO CONCLUIDA
echo  Os testes automatizados foram aprovados.
echo ==========================================================
echo.
pause
