<#
.SYNOPSIS
    Bumps the version of COMchecker and creates a Git tag.
.DESCRIPTION
    Updates version in:
      - src/version.py
      - version.json
      - installer.iss
    Then commits, pushes, tags, and pushes the tag.
.PARAMETER Version
    Explicit version string (e.g. "1.0.1.0"). If omitted, increments patch.
.PARAMETER Message
    Custom commit message. Default: "Release v{version}"
.PARAMETER NoPush
    Only commit and tag locally, don't push.
.EXAMPLE
    .\bump.ps1                     # Patch +1 -> 1.0.1.0
    .\bump.ps1 -Version 1.1.0.0   # Set explicit version
    .\bump.ps1 -NoPush             # Local only
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

# Update src/version.py
Set-Value -Path "$ProjectRoot\src\version.py" `
    -Pattern 'VERSION\s*=\s*"[^"]*"' `
    -NewValue "VERSION = `"$Version`""

# Update version.json
Set-Value -Path "$ProjectRoot\version.json" `
    -Pattern '"version":\s*"[^"]+"' `
    -NewValue "`"version`": `"$Version`""

# Update installer.iss
Set-Value -Path "$ProjectRoot\installer.iss" `
    -Pattern '#define MyAppVersion "[^"]*"' `
    -NewValue "#define MyAppVersion `"$Version`""

Write-Host "Updated all version references."

# Git operations: commit & push FIRST, then tag (so release never precedes code)
$commitMsg = if ($Message) { $Message } else { "Release v$Version" }

Set-Location -Path $ProjectRoot
git add -A
git commit -m $commitMsg

if (-not $NoPush) {
    git push origin HEAD:master
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Push failed. Tag was NOT created. Fix and retry."
        exit 1
    }
}

git tag "v$Version"

if (-not $NoPush) {
    git push origin "v$Version"
    Write-Host "Pushed commit and tag v$Version"
} else {
    Write-Host "Local commit and tag created (not pushed)."
}

Write-Host "Done."
