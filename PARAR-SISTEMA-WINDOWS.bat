@echo off
chcp 65001 >nul
title Facil Pedido ERP - Encerrar

powershell -NoProfile -Command ^
  "$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; " ^
  "if ($connections) { " ^
  "  $connections | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { " ^
  "    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue " ^
  "  }; " ^
  "  Write-Host 'Servidor encerrado.' " ^
  "} else { Write-Host 'Nenhum servidor usando a porta 8000.' }"

pause
