@echo off
chcp 65001 >nul
title Facil Pedido ERP - Backup da Homologacao
cd /d "%~dp0"

if not exist "backup\homologacao" mkdir "backup\homologacao"

if not exist "data\facil_pedido_homologacao.db" (
  echo.
  echo Ainda nao existe um banco de homologacao.
  echo Abra o sistema pelo arquivo ABRIR-HOMOLOGACAO-CLIENTE-WINDOWS.bat primeiro.
  echo.
  pause
  exit /b 1
)

for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set DATA=%%d-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set HORA=%%a-%%b
set HORA=%HORA: =0%

copy /Y "data\facil_pedido_homologacao.db" "backup\homologacao\facil_pedido_homologacao_%DATA%_%HORA%.db" >nul

echo.
echo Backup da homologacao criado com sucesso.
echo Pasta: backup\homologacao
echo.
pause
