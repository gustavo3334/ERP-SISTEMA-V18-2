@echo off
chcp 65001 >nul
title Facil Pedido ERP - Testes
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  call INSTALAR-WINDOWS.bat
  if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m pytest -q
pause
