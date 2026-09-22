@echo off
chcp 65001 >nul
title Facil Pedido ERP - Verificacao completa
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call INSTALAR-WINDOWS.bat
  if errorlevel 1 exit /b 1
)
call ".venv\Scripts\activate.bat"
python -m alembic upgrade head
if errorlevel 1 goto :erro
python -m pytest -q
if errorlevel 1 goto :erro
echo.
echo VERIFICACAO CONCLUIDA COM SUCESSO.
echo.
pause
exit /b 0
:erro
echo.
echo A verificacao encontrou um erro. Envie a tela para analise.
echo.
pause
exit /b 1
