param(
    [switch]$NoInstall,
    [string]$Name = "desktop_fences_lite_v6"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = Join-Path $Root "desktop_fences_lite.py"
$Dist = Join-Path $Root "dist"

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Source file not found: $Source"
}

python -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    if ($NoInstall) {
        throw "PyInstaller is not available."
    }
    python -m pip install pyinstaller
}

python -m PyInstaller --clean --onefile --windowed --name $Name --distpath $Dist --workpath (Join-Path $Root "build") --specpath $Root $Source
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Write-Host "Built: $(Join-Path $Dist ($Name + '.exe'))" -ForegroundColor Green

