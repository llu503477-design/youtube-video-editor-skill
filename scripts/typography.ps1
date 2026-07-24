#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$packScript = Join-Path $scriptRoot "..\youtube-video-typography-devpack\scripts\typography.ps1"

if (-not (Test-Path -LiteralPath $packScript -PathType Leaf)) {
    throw "Typography subproject not found: $packScript. Run the integration with youtube-video-typography-devpack first."
}

& $packScript @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
