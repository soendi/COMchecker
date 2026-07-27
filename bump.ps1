<#
.SYNOPSIS
    Bumps version, builds EXE + Installer, creates GitHub Release.
.DESCRIPTION
    Updates version in src/version.py, version.json, installer.iss,
    commits, pushes, builds COMchecker.exe + COMchecker-Setup.exe,
    tags, and creates a GitHub release with both assets.
.PARAMETER Version
    Explicit version string (e.g. "1.0.1.0"). If omitted, increments patch.
.PARAMETER Message
    Custom commit message. Default: "Release v{version}"
.PARAMETER NoRelease
    Only commit locally, skip build + tag + release.
.EXAMPLE
    .\bump.ps1                     # Patch +1 -> Release
    .\bump.ps1 -Version 2.0.0.0   # Set explicit version
    .\bump.ps1 -NoRelease          # Version bump + commit only
#>

param(
    [string]$Version,
    [string]$Message,
    [switch]$NoRelease
)

function Get-Value {
    param($Path, $Pattern)
    $content = Get-Content -Path $Path -Raw
    if ($content -match $Pattern) {
        return $Matches[1]
    }
    return $null
}

function Set-Value {
    param($Path, $Pattern, $NewValue)
    $content = Get-Content -Path $Path -Raw
    $content = $content -replace $Pattern, $NewValue
    Set-Content -Path $Path -Value $content -NoNewline
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorActionPreference = "Stop"

# Detect ISCC
$isccPaths = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"
)
$iscc = $null
foreach ($p in $isccPaths) {
    if (Test-Path -LiteralPath $p) { $iscc = $p; break }
}

# Read current version
$currentVersion = Get-Value -Path "$ProjectRoot\version.json" -Pattern '"version":\s*"([^"]+)"'
Write-Host "Current version: $currentVersion"

# Determine new version
if (-not $Version) {
    $parts = $currentVersion -split '\.'
    $patch = [int]$parts[3] + 1
    $Version = "$($parts[0]).$($parts[1]).$($parts[2]).$patch"
}
Write-Host "New version:     $Version"

# Update version files
Set-Value -Path "$ProjectRoot\src\version.py" `
    -Pattern 'VERSION\s*=\s*"[^"]*"' `
    -NewValue "VERSION = `"$Version`""

Set-Value -Path "$ProjectRoot\version.json" `
    -Pattern '"version":\s*"[^"]+"' `
    -NewValue "`"version`": `"$Version`""

Set-Value -Path "$ProjectRoot\installer.iss" `
    -Pattern '#define MyAppVersion "[^"]*"' `
    -NewValue "#define MyAppVersion `"$Version`""

Write-Host "Updated all version references."

$ErrorActionPreference = "Continue"  # native commands (pyinstaller) write info to stderr
Set-Location -Path $ProjectRoot
$commitMsg = if ($Message) { $Message } else { "Release v$Version" }

# --- Git commit + push (no tag yet) ---
git add -A
git commit -m $commitMsg

if (-not $NoRelease) {
    git push origin HEAD:master
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Push failed. Aborting."
        exit 1
    }
}

# --- Build EXE + Installer ---
if (-not $NoRelease) {
    Write-Host "`nBuilding COMchecker.exe with PyInstaller..."
    pyinstaller --onefile --windowed --name "COMchecker" `
        --icon "$ProjectRoot\resources\icon.ico" `
        --add-data "$ProjectRoot\resources;resources" `
        --distpath "$ProjectRoot\dist" `
        --workpath "$ProjectRoot\build" `
        --specpath "$ProjectRoot" `
        "$ProjectRoot\src\main.py" *>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: PyInstaller failed."; exit 1 }

    if (-not $iscc) {
        Write-Host "ERROR: ISCC.exe not found. Install Inno Setup or set path."
        exit 1
    }
    Write-Host "Building COMchecker-Setup.exe with Inno Setup..."
    & $iscc "$ProjectRoot\installer.iss" *>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: ISCC failed."; exit 1 }
}

# --- Git tag (only after successful build) ---
git tag "v$Version"

if (-not $NoRelease) {
    git push origin "v$Version"
    Write-Host "`nCreating GitHub Release v$Version..."
    gh release create "v$Version" `
        --title "COMchecker v$Version" `
        --notes "Release v$Version" `
        "$ProjectRoot\dist\COMchecker.exe" `
        "$ProjectRoot\dist\COMchecker-Setup.exe"
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: gh release create failed."; exit 1 }
    Write-Host "Pushed commit, tag v$Version, and created release."
} else {
    Write-Host "Local commit created (no tag, no build)."
}

Write-Host "Done."
