@echo off
chcp 65001 >nul
title Facil Pedido ERP - Reset da Homologacao
cd /d "%~dp0"

echo.
echo ===========================================================
echo  ATENCAO
echo  Esta acao apaga SOMENTE os dados do ambiente de homologacao.
echo  O banco principal nao sera alterado.
echo ===========================================================
echo.
set /p CONFIRMA=Digite APAGAR TESTES para continuar: 

if /I not "%CONFIRMA%"=="APAGAR TESTES" (
  echo.
  echo Operacao cancelada.
  pause
  exit /b 0
)

if exist "data\facil_pedido_homologacao.db" del /Q "data\facil_pedido_homologacao.db"
if exist "storage\homologacao\uploads" (
  rmdir /S /Q "storage\homologacao\uploads"
)
mkdir "storage\homologacao\uploads" >nul 2>nul

echo.
echo Ambiente de homologacao zerado.
echo Na proxima abertura o banco vazio sera recriado.
echo.
pause
