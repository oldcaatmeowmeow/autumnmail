$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root "web")
if (-not (Test-Path "node_modules")) {
    npm install --no-audit --no-fund
}
npm run build
Pop-Location
Write-Host "前端已构建到 autumnmail/web" -ForegroundColor Green
