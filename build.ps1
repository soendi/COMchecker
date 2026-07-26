<#
.SYNOPSIS
    Builds COMchecker executable and installer.
.DESCRIPTION
    Runs PyInstaller to create a single-file exe,
    then compiles the Inno Setup installer.
#>

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $ProjectRoot

Write-Host "=== Step 1: Install dependencies ==="
pip install -r requirements.txt
pip install pyinstaller

Write-Host "`n=== Step 2: Build executable ==="
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
}
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

$iconPath = "resources\icon.ico"
$iconArg = if (Test-Path $iconPath) { "--icon=$iconPath" } else { "" }

pyinstaller --onefile --windowed $iconArg --name COMchecker --add-data "resources;resources" src\main.py

if (-not (Test-Path "dist\COMchecker.exe")) {
    Write-Host "ERROR: PyInstaller build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 3: Compile installer ==="
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) {
    & $iscc installer.iss
    if (Test-Path "COMchecker-Setup.exe") {
        Write-Host "`nInstaller created: COMchecker-Setup.exe" -ForegroundColor Green
    }
} else {
    Write-Host "Inno Setup not found at $iscc" -ForegroundColor Yellow
    Write-Host "Install Inno Setup 6 from: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
}

Write-Host "`n=== Done ==="
