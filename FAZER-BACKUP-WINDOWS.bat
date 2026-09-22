@echo off
chcp 65001 >nul
title Facil Pedido ERP - Backup completo
cd /d "%~dp0"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set MOMENTO=%%i
set DESTINO=backup\backup_%MOMENTO%

if not exist "backup" mkdir "backup"
mkdir "%DESTINO%" >nul 2>nul

if exist "data\facil_pedido.db" (
  copy /Y "data\facil_pedido.db" "%DESTINO%\facil_pedido.db" >nul
  echo Banco copiado.
) else (
  echo Aviso: banco local ainda nao existe.
)

if exist "storage\uploads" (
  xcopy /E /I /Y "storage\uploads" "%DESTINO%\uploads" >nul
  echo Documentos copiados.
)

if exist ".env" copy /Y ".env" "%DESTINO%\.env.backup" >nul

echo.
echo Backup criado em:
echo %DESTINO%
echo.
pause
