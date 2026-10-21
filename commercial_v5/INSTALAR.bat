@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo  FACIL PEDIDO V7 - INSTALACAO LOCAL
echo ================================================
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale Python 3.11 ou superior e marque Add Python to PATH.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo Falha ao instalar dependencias.
  pause
  exit /b 1
)
echo.
echo Instalacao concluida.
pause
