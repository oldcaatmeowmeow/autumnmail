$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# M0 仅提供脚本占位；正式打包在 M4 完成。
# 依赖：pip install -e ".[build]"
# Nuitka 打包 pywebview/pythonnet 时需在 Windows 上验证。

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "请先运行 scripts/dev.ps1 准备环境"
}

Write-Host "==> 检查 Nuitka" -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m nuitka --version
if ($LASTEXITCODE -ne 0) {
    throw '未安装 Nuitka，请运行：.\.venv\Scripts\python.exe -m pip install ".[build]"'
}

Write-Host "==> 构建前端" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "build_web.ps1")

Write-Host "==> Nuitka standalone" -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m nuitka `
    --standalone `
    --assume-yes-for-downloads `
    --windows-console-mode=disable `
    --enable-plugin=pywebview `
    --include-data-dir="autumnmail/web=autumnmail/web" `
    --include-package=autumnmail `
    --output-dir=dist `
    -m autumnmail

Write-Host "完成：dist/autumnmail.dist" -ForegroundColor Green
