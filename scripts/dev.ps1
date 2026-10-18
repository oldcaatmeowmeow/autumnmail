$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> 准备 Python 环境" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -q

Write-Host "==> 构建前端" -ForegroundColor Cyan
Push-Location web
if (-not (Test-Path "node_modules")) {
    npm install --no-audit --no-fund
}
npm run build
Pop-Location

Write-Host "==> 启动 AutumnMail（开发模式）" -ForegroundColor Cyan
$env:AUTUMNMAIL_TOKEN = "dev-token"
.\.venv\Scripts\python.exe -m autumnmail --dev
