<#
.SYNOPSIS
    Bumps version and pushes tag – GitHub Actions baut EXE + Installer + Release.
.DESCRIPTION
    Updates version in src/version.py, version.json, installer.iss,
    commits, pushes, creates and pushes a tag.
    GitHub Actions (release.yml) baut dann PyInstaller-EXE + Inno Setup-Installer
    und erstellt das GitHub Release automatisch.
.PARAMETER Version
    Explicit version string (e.g. "1.0.1.0"). If omitted, increments patch.
.PARAMETER Message
    Custom commit message. Default: "Release v{version}"
.PARAMETER NoPush
    Only commit locally, skip push + tag.
.EXAMPLE
    .\bump.ps1                   # Patch +1 -> GitHub baut Release
    .\bump.ps1 -Version 2.0.0.0 # Set explicit version
    .\bump.ps1 -NoPush           # Version bump + commit only
#>

param(
    [string]$Version,
    [string]$Message,
    [switch]$NoPush
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

Set-Location -Path $ProjectRoot
$commitMsg = if ($Message) { $Message } else { "Release v$Version" }

# --- Git commit ---
git add -A
git commit -m $commitMsg

# --- Push + Tag (GitHub Actions baut dann Release) ---
if (-not $NoPush) {
    git push origin HEAD:master
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Push failed. Aborting."
        exit 1
    }

    git tag "v$Version"
    git push origin "v$Version"
    Write-Host "Tag v$Version pushed. GitHub Actions buildet jetzt EXE + Installer + Release."
} else {
    Write-Host "Local commit created (not pushed)."
}

Write-Host "Done."
