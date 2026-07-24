#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [string]$OutputPath,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $projectRoot "out\demo-remotion.mp4"
}
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $resolvedOutput -PathType Container) {
    throw "Output path must be a file: $resolvedOutput"
}
if ((Test-Path -LiteralPath $resolvedOutput) -and -not $Force) {
    throw "Output already exists: $resolvedOutput. Use -Force only with explicit permission."
}

$outputParent = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outputParent | Out-Null
$stagedOutput = Join-Path $outputParent (
    ".demo-remotion-" + [guid]::NewGuid().ToString("N") + ".mp4"
)
$remotion = Join-Path $projectRoot "node_modules\.bin\remotion.cmd"
if (-not (Test-Path -LiteralPath $remotion -PathType Leaf)) {
    throw "Remotion is not installed. Run npm ci first."
}
$ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
if (-not $ffprobe) {
    throw "FFprobe is required to validate the rendered demo."
}
$propsPath = Join-Path $projectRoot "..\..\examples\demo.plan.json"
$backup = $null

Push-Location $projectRoot
try {
    & $remotion render src/index.ts DynamicTypography $stagedOutput "--props=$propsPath"
    if ($LASTEXITCODE -ne 0 -or
        -not (Test-Path -LiteralPath $stagedOutput -PathType Leaf) -or
        (Get-Item -LiteralPath $stagedOutput).Length -le 0) {
        throw "Remotion demo render failed. Staged output retained at: $stagedOutput"
    }
    & $ffprobe.Source -v error -select_streams v:0 `
        -show_entries stream=codec_name,width,height:format=duration,size `
        -of json $stagedOutput | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "FFprobe rejected the Remotion output. Staged output retained at: $stagedOutput"
    }

    if (Test-Path -LiteralPath $resolvedOutput -PathType Leaf) {
        if (-not $Force) {
            throw "Output appeared during rendering and was not overwritten: $resolvedOutput"
        }
        $backup = "$resolvedOutput.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
        Move-Item -LiteralPath $resolvedOutput -Destination $backup
    }
    try {
        Move-Item -LiteralPath $stagedOutput -Destination $resolvedOutput
    } catch {
        if ($backup -and
            -not (Test-Path -LiteralPath $resolvedOutput) -and
            (Test-Path -LiteralPath $backup -PathType Leaf)) {
            Move-Item -LiteralPath $backup -Destination $resolvedOutput
        }
        throw
    }
} finally {
    Pop-Location
}

Write-Host "[OK] Remotion demo: $resolvedOutput" -ForegroundColor Green
if ($backup) {
    Write-Host "[BACKUP] $backup" -ForegroundColor Yellow
}
