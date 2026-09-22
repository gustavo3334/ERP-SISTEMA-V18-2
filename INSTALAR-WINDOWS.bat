@echo off
chcp 65001 >nul
title Facil Pedido ERP - Instalacao
cd /d "%~dp0"

echo ================================================
echo  FACIL PEDIDO ERP - INSTALACAO WINDOWS
echo ================================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if %errorlevel%==0 set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if %errorlevel%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo [ERRO] Python nao foi encontrado.
  echo Instale Python 3.11 ou mais recente e marque Add Python to PATH.
  echo.
  pause
  exit /b 1
)

echo Python encontrado.

if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto erro
)

echo Atualizando pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto erro

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erro

if not exist ".env" copy /Y ".env.example" ".env" >nul
if not exist "data" mkdir "data"
if not exist "storage" mkdir "storage"

echo Preparando banco de dados...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 goto erro

echo Preparando configuracao inicial...
".venv\Scripts\python.exe" -m app.seed
if errorlevel 1 goto erro

echo.
echo ================================================
echo  INSTALACAO CONCLUIDA COM SUCESSO
echo ================================================
echo.
echo Agora execute:
echo ABRIR-HOMOLOGACAO-CLIENTE-WINDOWS.bat
echo.
pause
exit /b 0

:erro
echo.
echo [ERRO] A instalacao nao foi concluida.
echo Envie uma captura desta janela com a mensagem acima.
echo.
pause
exit /b 1
