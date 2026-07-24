#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [Alias("InputPath")]
    [string]$InputVideo,

    [Parameter(Mandatory = $true)]
    [string]$PlanPath,

    [Parameter(Mandatory = $true)]
    [Alias("OutputPath")]
    [string]$OutputVideo,

    [string]$AssPath,

    [ValidateRange(0, 51)]
    [int]$Crf = 20,

    [switch]$Force
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Assert-Command {
    param([string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Required command not found: $Name"
    }
    return $command.Source
}

function ConvertTo-AssFilterPath {
    param([string]$Path)
    $full = [System.IO.Path]::GetFullPath($Path)
    return $full.Replace('\', '/').Replace(':', '\:').Replace("'", "\'")
}

$ffmpeg = Assert-Command "ffmpeg"
$ffprobe = Assert-Command "ffprobe"
$python = Assert-Command "python"

if (-not (Test-Path -LiteralPath $InputVideo -PathType Leaf)) {
    throw "Input video not found: $InputVideo"
}
if (-not (Test-Path -LiteralPath $PlanPath -PathType Leaf)) {
    throw "Visual plan not found: $PlanPath"
}
if (Test-Path -LiteralPath $OutputVideo -PathType Container) {
    throw "Output path must be a file, not a directory: $OutputVideo"
}
if ((Test-Path -LiteralPath $OutputVideo) -and -not $Force) {
    throw "Output already exists: $OutputVideo. Use -Force only with explicit permission."
}

$resolvedInput = [System.IO.Path]::GetFullPath($InputVideo)
$resolvedPlan = [System.IO.Path]::GetFullPath($PlanPath)
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputVideo)
if ($resolvedInput -eq $resolvedOutput) {
    throw "Output video must not overwrite the input video."
}

$outputParent = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outputParent | Out-Null

$usesExistingAss = -not [string]::IsNullOrWhiteSpace($AssPath)
if (-not $usesExistingAss) {
    $outputStem = [System.IO.Path]::GetFileNameWithoutExtension($OutputVideo)
    if (-not $outputStem.EndsWith(".typography", [System.StringComparison]::OrdinalIgnoreCase)) {
        $outputStem += ".typography"
    }
    $AssPath = Join-Path $outputParent "$outputStem.ass"
}
$resolvedAss = [System.IO.Path]::GetFullPath($AssPath)
if ($resolvedAss -eq $resolvedOutput -or
    $resolvedAss -eq $resolvedPlan -or
    $resolvedAss -eq $resolvedInput) {
    throw "ASS output must use a path distinct from the input, output, and visual plan."
}
if (Test-Path -LiteralPath $resolvedAss -PathType Container) {
    throw "ASS path must be a file, not a directory: $resolvedAss"
}
if ($usesExistingAss -and -not (Test-Path -LiteralPath $resolvedAss -PathType Leaf)) {
    throw "Pre-generated ASS file not found: $resolvedAss"
}
if (-not $usesExistingAss -and (Test-Path -LiteralPath $resolvedAss) -and -not $Force) {
    throw "ASS output already exists: $resolvedAss. Use -Force only with explicit permission."
}

$stagingDirectory = Join-Path $outputParent (
    ".typography-render-" + [guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $stagingDirectory | Out-Null
$stagedAss = Join-Path $stagingDirectory "captions.ass"
$stagedVideo = Join-Path $stagingDirectory (
    "rendered" + [System.IO.Path]::GetExtension($resolvedOutput)
)

$validatorArgs = @(
    (Join-Path $scriptRoot "validate_typography_project.py"),
    $resolvedPlan
)
& $python @validatorArgs
if ($LASTEXITCODE -ne 0) {
    throw "Visual plan validation failed. Staging retained at: $stagingDirectory"
}

if ($usesExistingAss) {
    Copy-Item -LiteralPath $resolvedAss -Destination $stagedAss
} else {
    $assArgs = @(
        (Join-Path $scriptRoot "generate_dynamic_ass.py"),
        $resolvedPlan,
        $stagedAss
    )

    & $python @assArgs
    if ($LASTEXITCODE -ne 0) {
        throw "ASS generation failed with exit code $LASTEXITCODE. Staging retained at: $stagingDirectory"
    }
}
if (-not (Test-Path -LiteralPath $stagedAss -PathType Leaf) -or
    (Get-Item -LiteralPath $stagedAss).Length -le 0) {
    throw "ASS input is empty or unavailable. Staging retained at: $stagingDirectory"
}

$filterPath = ConvertTo-AssFilterPath $stagedAss
$ffmpegArgs = @(
    "-n",
    "-hide_banner",
    "-i", $resolvedInput,
    "-vf", "ass='$filterPath'",
    "-c:v", "libx264",
    "-crf", $Crf.ToString(),
    "-preset", "medium",
    "-c:a", "aac",
    "-b:a", "192k",
    "-movflags", "+faststart",
    $stagedVideo
)

& $ffmpeg @ffmpegArgs
if ($LASTEXITCODE -ne 0 -or
    -not (Test-Path -LiteralPath $stagedVideo -PathType Leaf) -or
    (Get-Item -LiteralPath $stagedVideo).Length -le 0) {
    throw "FFmpeg typography render failed. Staging retained at: $stagingDirectory"
}

$probeArgs = @(
    "-v", "error",
    "-show_entries", "format=duration,size:stream=index,codec_type,codec_name",
    "-of", "json",
    $stagedVideo
)
$probeOutput = & $ffprobe @probeArgs
if ($LASTEXITCODE -ne 0) {
    throw "FFprobe validation failed. Staging retained at: $stagingDirectory"
}

$artifacts = @(
    @{ Stage = $stagedVideo; Final = $resolvedOutput }
)
if (-not $usesExistingAss) {
    $artifacts = @(
        @{ Stage = $stagedAss; Final = $resolvedAss },
        @{ Stage = $stagedVideo; Final = $resolvedOutput }
    )
}
$backups = @{}
$published = [System.Collections.Generic.List[hashtable]]::new()
$backupStamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"

try {
    foreach ($artifact in $artifacts) {
        if (Test-Path -LiteralPath $artifact.Final -PathType Leaf) {
            if (-not $Force) {
                throw "Output appeared during rendering and was not overwritten: $($artifact.Final)"
            }
            $backup = "$($artifact.Final).backup-$backupStamp"
            Move-Item -LiteralPath $artifact.Final -Destination $backup
            $backups[$artifact.Final] = $backup
        }
    }
    foreach ($artifact in $artifacts) {
        Move-Item -LiteralPath $artifact.Stage -Destination $artifact.Final
        $published.Add($artifact)
    }
} catch {
    foreach ($artifact in @($published)) {
        if (Test-Path -LiteralPath $artifact.Final -PathType Leaf) {
            Move-Item -LiteralPath $artifact.Final -Destination $artifact.Stage
        }
    }
    foreach ($finalPath in @($backups.Keys)) {
        if (-not (Test-Path -LiteralPath $finalPath) -and
            (Test-Path -LiteralPath $backups[$finalPath] -PathType Leaf)) {
            Move-Item -LiteralPath $backups[$finalPath] -Destination $finalPath
        }
    }
    throw "Typography publication failed. Staging retained at '$stagingDirectory'. $($_.Exception.Message)"
}

if ($usesExistingAss -and (Test-Path -LiteralPath $stagedAss -PathType Leaf)) {
    Remove-Item -LiteralPath $stagedAss
}
if (Test-Path -LiteralPath $stagingDirectory -PathType Container) {
    Remove-Item -LiteralPath $stagingDirectory
}

Write-Host "[OK] Rendered: $resolvedOutput" -ForegroundColor Green
if ($usesExistingAss) {
    Write-Host "[OK] ASS input: $resolvedAss" -ForegroundColor Green
} else {
    Write-Host "[OK] ASS generated: $resolvedAss" -ForegroundColor Green
}
Write-Host ($probeOutput -join [Environment]::NewLine)
foreach ($backup in $backups.Values) {
    Write-Host "[BACKUP] $backup" -ForegroundColor Yellow
}
