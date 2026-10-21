# Build the Windows release zip: dist/shrimply-win64.zip
# Usage: powershell -ExecutionPolicy Bypass -File tools\build_win.ps1
param([string]$ReleaseTag = "")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-Not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create virtual environment" }
}
if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt -e .
    if ($LASTEXITCODE -ne 0) { throw "Could not install build dependencies" }
    & uv pip check --python .venv\Scripts\python.exe
} else {
    & .venv\Scripts\python.exe -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare pip" }
    & .venv\Scripts\python.exe -m pip install -r requirements-dev.txt -e .
    if ($LASTEXITCODE -ne 0) { throw "Could not install build dependencies" }
    & .venv\Scripts\python.exe -m pip check
}
if ($LASTEXITCODE -ne 0) { throw "Build dependencies conflict" }
if ($ReleaseTag) {
    $installedVersion = & .venv\Scripts\python.exe -c "import importlib.metadata; print(importlib.metadata.version('shrimply'))"
    if ($LASTEXITCODE -ne 0 -or $ReleaseTag -ne "v$installedVersion") {
        throw "Release tag $ReleaseTag does not match app version v$installedVersion"
    }
}
& .venv\Scripts\python.exe fetch_models.py
if ($LASTEXITCODE -ne 0) { throw "Model verification failed" }

& .venv\Scripts\python.exe -m PyInstaller shrimply.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$smokePath = Join-Path $root "dist\shrimply-build-smoke.json"
if (Test-Path -LiteralPath $smokePath) { Remove-Item -LiteralPath $smokePath }
$smoke = Start-Process -FilePath (Join-Path $root "dist\shrimply\shrimply.exe") -ArgumentList @('--smoke-test', "`"$smokePath`"") -Wait -PassThru -WindowStyle Hidden
if ($smoke.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $smokePath) -or
    -not (Get-Content -LiteralPath $smokePath -Raw | ConvertFrom-Json).ok) {
    throw "Packaged executable smoke test failed"
}

if (Test-Path dist\shrimply-win64.zip) { Remove-Item dist\shrimply-win64.zip }
Compress-Archive -Path dist\shrimply -DestinationPath dist\shrimply-win64.zip
$mb = [math]::Round((Get-Item dist\shrimply-win64.zip).Length / 1MB, 1)
Write-Host "built dist\shrimply-win64.zip ($mb MB)"
