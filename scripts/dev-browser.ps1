# Run the sidecar + renderer in the browser (no Electron) in two windows.
#   powershell -ExecutionPolicy Bypass -File scripts\dev-browser.ps1
Set-Location (Join-Path $PSScriptRoot "..")
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services\sidecar; uv run python -m app --dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev -w apps/desktop"
Write-Host "Sidecar: http://127.0.0.1:8765/docs   App: http://localhost:5173"
