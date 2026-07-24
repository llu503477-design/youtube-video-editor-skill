#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [switch]$Force
)

$repo = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path -LiteralPath $repo -PathType Container)) {
    throw "Repository directory not found: $repo"
}

$expectedPack = Join-Path $repo "youtube-video-typography-devpack"
$currentPack = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([System.IO.Path]::GetFullPath($currentPack) -ne
    [System.IO.Path]::GetFullPath($expectedPack)) {
    throw "Place this complete directory at '$expectedPack'; overlay copying is no longer supported."
}

if ($Force) {
    Write-Host "-Force is ignored because subproject integration never overwrites root implementation." -ForegroundColor Yellow
}
Write-Host "Typography subproject is already in the canonical location." -ForegroundColor Green
Write-Host "Use the root entrypoint: scripts/typography.ps1" -ForegroundColor Cyan
