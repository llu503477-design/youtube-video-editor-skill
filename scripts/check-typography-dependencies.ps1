#!/usr/bin/env pwsh
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$packScript = Join-Path $PSScriptRoot "..\youtube-video-typography-devpack\scripts\check-typography-dependencies.ps1"

if (-not (Test-Path -LiteralPath $packScript -PathType Leaf)) {
    throw "Typography dependency checker not found: $packScript"
}

& $packScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
