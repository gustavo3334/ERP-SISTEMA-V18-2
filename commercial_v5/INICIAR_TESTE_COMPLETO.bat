@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo O ambiente ainda nao foi instalado. Executando instalacao...
  call INSTALAR.bat
)
echo Iniciando ERP de teste na porta 8000...
start "Facil Pedido - ERP teste" "%~dp0mock_erp\run_mock.bat"
timeout /t 3 /nobreak >nul
echo Iniciando Gateway integrado na porta 8010...
start "Facil Pedido - Gateway V5" "%~dp0gateway\run_gateway_test.bat"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:8010/"
timeout /t 1 /nobreak >nul
start "" "http://127.0.0.1:8010/site-demo.html"
echo.
echo TESTE PRONTO
echo ERP teste:     http://127.0.0.1:8000/api/v1
echo Gateway:       http://127.0.0.1:8010/api/v1
echo Swagger ERP:   http://127.0.0.1:8000/docs
echo Swagger Gate:  http://127.0.0.1:8010/docs
echo.
echo Logins:
echo Admin:  admin@facilpedido.local / TroqueEstaSenha123!
echo RH:     rh@facilpedido.local / RHcatalogo123!
echo Vendas: vendas@facilpedido.local / Vendas123!
echo.
pause
