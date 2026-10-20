# One-time setup on Windows 11 (PowerShell). Read-only checks first, then installs.
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "== Checking tools ==" -ForegroundColor Cyan
foreach ($tool in "git", "node", "npm") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool not found. Install it first (see README)." }
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv (Python package/version manager)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Write-Host "== Python 3.12 for the sidecar (your system Python 3.14 is untouched) ==" -ForegroundColor Cyan
uv python install 3.12
Push-Location services\sidecar
uv sync
uv run alembic upgrade head
Pop-Location

Write-Host "== Node dependencies ==" -ForegroundColor Cyan
npm install

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "Ollama found. Optional: 'ollama pull qwen3:4b' for the AI coach." -ForegroundColor Green
} else {
    Write-Host "Ollama not found: the coach will use rule-based tips (everything else works)." -ForegroundColor Yellow
}
Write-Host "Done. Start the app with: npm run dev:electron -w apps/desktop" -ForegroundColor Green
