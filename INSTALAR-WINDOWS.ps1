$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== FACIL PEDIDO ERP - INSTALACAO ==="

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $python = @("py", "-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $python = @("python") }
else { throw "Python 3.11+ nao foi encontrado. Instale o Python e habilite Add Python to PATH." }

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "Criando ambiente virtual..."
  if ($python.Count -eq 2) { & $python[0] $python[1] -m venv .venv } else { & $python[0] -m venv .venv }
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
New-Item -ItemType Directory -Force -Path "data" | Out-Null
New-Item -ItemType Directory -Force -Path "storage" | Out-Null
& $venvPython -m alembic upgrade head
& $venvPython -m app.seed
Write-Host ""
Write-Host "INSTALACAO CONCLUIDA." -ForegroundColor Green
Write-Host "Agora execute .\ABRIR-HOMOLOGACAO-CLIENTE-WINDOWS.bat"
