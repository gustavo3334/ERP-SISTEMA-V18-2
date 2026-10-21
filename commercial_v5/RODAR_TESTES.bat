@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Instale o ambiente antes com INSTALAR.bat.
  pause
  exit /b 1
)
echo Testes automatizados: ERP ficticio e Gateway usam bancos temporarios.
"%~dp0.venv\Scripts\python.exe" "%~dp0tests\test_e2e_local.py"
if errorlevel 1 (
 echo Houve falha em pelo menos um teste.
 pause
 exit /b 1
)
echo Todos os testes automatizados passaram.
pause
