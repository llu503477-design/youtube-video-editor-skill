#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$required = @("ffmpeg", "ffprobe", "python")
$optional = @("node", "npm")
$failed = $false

Write-Host "========================================"
Write-Host "Video Typography - Dependency Check"
Write-Host "========================================"

foreach ($name in $required) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) {
        Write-Host "[  OK  ] $name" -ForegroundColor Green
    } else {
        Write-Host "[FAILED] $name" -ForegroundColor Red
        $failed = $true
    }
}

foreach ($name in $optional) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) {
        Write-Host "[  OK  ] $name (optional)" -ForegroundColor Green
    } else {
        Write-Host "[ SKIP ] $name (optional)" -ForegroundColor Yellow
    }
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpeg) {
    $filters = & $ffmpeg.Source -hide_banner -filters 2>&1
    $hasAss = ($filters -join "`n") -match "(?m)^\s*[TSC\.]+\s+ass\s+"
    $hasSubtitles = ($filters -join "`n") -match "(?m)^\s*[TSC\.]+\s+subtitles\s+"

    if ($hasAss -or $hasSubtitles) {
        Write-Host "[  OK  ] FFmpeg libass subtitle filter" -ForegroundColor Green
    } else {
        Write-Host "[FAILED] FFmpeg does not expose ass/subtitles filter" -ForegroundColor Red
        $failed = $true
    }
}

if ($failed) {
    exit 1
}
exit 0
