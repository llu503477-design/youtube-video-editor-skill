#!/usr/bin/env pwsh
param(
    [string]$VideoPath,
    [string]$SrtPath,
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$allPassed = $true

function Write-TestResult {
    param(
        [string]$Name,
        [ValidateSet("PASS", "FAIL", "SKIP", "WARN")]
        [string]$Status,
        [string]$Detail
    )

    $colors = @{
        PASS = "Green"
        FAIL = "Red"
        SKIP = "DarkGray"
        WARN = "Yellow"
    }
    Write-Host "[$Status] $Name" -ForegroundColor $colors[$Status]
    if ($Detail) {
        Write-Host "       $Detail"
    }
    if ($Status -eq "FAIL") {
        $script:allPassed = $false
    }
}

function Test-Executable {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [string]$ExpectedPattern,
        [switch]$Optional
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        $status = if ($Optional) { "SKIP" } else { "FAIL" }
        Write-TestResult -Name "$Name available" -Status $status -Detail "Command not found in PATH."
        return $false
    }

    try {
        $output = & $command.Source @Arguments 2>&1
        $outputText = $output -join [Environment]::NewLine
        $matched = $LASTEXITCODE -eq 0 -and $outputText -match $ExpectedPattern
        $status = if ($matched) { "PASS" } elseif ($Optional) { "WARN" } else { "FAIL" }
        $detail = ($output | Select-Object -First 1).ToString().Trim()
        Write-TestResult -Name "$Name available" -Status $status -Detail $detail
        return $matched
    } catch {
        $status = if ($Optional) { "WARN" } else { "FAIL" }
        Write-TestResult -Name "$Name available" -Status $status -Detail $_.Exception.Message
        return $false
    }
}

function Get-ProbeValue {
    param(
        [string[]]$ProbeOutput,
        [string]$Key
    )

    $line = $ProbeOutput | Where-Object { $_ -like "$Key=*" } | Select-Object -First 1
    if ($null -eq $line) {
        return $null
    }
    return $line.Substring($Key.Length + 1)
}

Write-Host "========================================"
Write-Host "YouTube Video Editor - Validation Report"
Write-Host "========================================"
Write-Host ""

Write-Host "--- Environment Checks ---"
$hasFfmpeg = Test-Executable -Name "ffmpeg" -Arguments @("-version") -ExpectedPattern "ffmpeg version"
$hasFfprobe = Test-Executable -Name "ffprobe" -Arguments @("-version") -ExpectedPattern "ffprobe version"
$null = Test-Executable -Name "auto-editor" -Arguments @("--version") -ExpectedPattern "^\d+\.\d+\.\d+$" -Optional

if ($VideoPath) {
    Write-Host ""
    Write-Host "--- Input Video Checks ---"
    if (-not (Test-Path -LiteralPath $VideoPath -PathType Leaf)) {
        Write-TestResult -Name "Input video" -Status "FAIL" -Detail "File not found: $VideoPath"
    } elseif (-not $hasFfprobe) {
        Write-TestResult -Name "Input video probe" -Status "SKIP" -Detail "FFprobe is unavailable."
    } else {
        $resolvedVideo = (Resolve-Path -LiteralPath $VideoPath).Path
        $formatProbe = @(& ffprobe -v error -show_entries format=duration,size,bit_rate -of default=noprint_wrappers=1 $resolvedVideo 2>&1)
        if ($LASTEXITCODE -ne 0) {
            Write-TestResult -Name "Video readable" -Status "FAIL" -Detail ($formatProbe -join " ")
        } else {
            $duration = Get-ProbeValue -ProbeOutput $formatProbe -Key "duration"
            $size = Get-ProbeValue -ProbeOutput $formatProbe -Key "size"
            $durationValid = $null -ne $duration -and [double]$duration -gt 0
            Write-TestResult -Name "Video readable" -Status $(if ($durationValid) { "PASS" } else { "FAIL" }) -Detail "Duration: ${duration}s, Size: $size bytes"

            $videoStream = @(& ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 $resolvedVideo 2>&1)
            $codec = Get-ProbeValue -ProbeOutput $videoStream -Key "codec_name"
            $width = Get-ProbeValue -ProbeOutput $videoStream -Key "width"
            $height = Get-ProbeValue -ProbeOutput $videoStream -Key "height"
            Write-TestResult -Name "Video stream present" -Status $(if ($codec) { "PASS" } else { "FAIL" }) -Detail "Codec: $codec, Resolution: ${width}x${height}"

            $audioStream = @(& ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1 $resolvedVideo 2>&1)
            $audioCodec = Get-ProbeValue -ProbeOutput $audioStream -Key "codec_name"
            Write-TestResult -Name "Audio stream present" -Status $(if ($audioCodec) { "PASS" } else { "WARN" }) -Detail $(if ($audioCodec) { "Codec: $audioCodec" } else { "No audio stream; valid for silent video." })
        }
    }
} else {
    Write-TestResult -Name "Input video checks" -Status "SKIP" -Detail "No -VideoPath supplied."
}

if ($SrtPath) {
    Write-Host ""
    Write-Host "--- Subtitle Checks ---"
    if (-not (Test-Path -LiteralPath $SrtPath -PathType Leaf)) {
        Write-TestResult -Name "Subtitle file" -Status "FAIL" -Detail "File not found: $SrtPath"
    } else {
        $srtContent = Get-Content -LiteralPath $SrtPath -Raw -Encoding UTF8
        $hasSequence = $srtContent -match '(?m)^\d+\s*$'
        $hasTimestamp = $srtContent -match '(?m)^\d{2,}:\d{2}:\d{2}[,.]\d{3}\s+-->\s+\d{2,}:\d{2}:\d{2}[,.]\d{3}\s*$'
        Write-TestResult -Name "SRT has sequence numbers" -Status $(if ($hasSequence) { "PASS" } else { "FAIL" }) -Detail ""
        Write-TestResult -Name "SRT has timestamps" -Status $(if ($hasTimestamp) { "PASS" } else { "FAIL" }) -Detail ""
        $entryCount = ([regex]::Matches($srtContent, '(?m)^\d+\s*$')).Count
        Write-TestResult -Name "SRT has entries" -Status $(if ($entryCount -gt 0) { "PASS" } else { "FAIL" }) -Detail "Entries: $entryCount"
    }
} else {
    Write-TestResult -Name "Subtitle checks" -Status "SKIP" -Detail "No -SrtPath supplied."
}

if ($OutputPath) {
    Write-Host ""
    Write-Host "--- Output Verification ---"
    if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        Write-TestResult -Name "Output file" -Status "FAIL" -Detail "File not found: $OutputPath"
    } elseif (-not $hasFfprobe) {
        Write-TestResult -Name "Output probe" -Status "SKIP" -Detail "FFprobe is unavailable."
    } else {
        $resolvedOutput = (Resolve-Path -LiteralPath $OutputPath).Path
        $outProbe = @(& ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 $resolvedOutput 2>&1)
        $outDuration = Get-ProbeValue -ProbeOutput $outProbe -Key "duration"
        $outSize = Get-ProbeValue -ProbeOutput $outProbe -Key "size"
        $valid = $LASTEXITCODE -eq 0 -and $null -ne $outDuration -and [double]$outDuration -gt 0 -and [long]$outSize -gt 0
        $sizeMb = if ($outSize) { [math]::Round([long]$outSize / 1MB, 2) } else { 0 }
        Write-TestResult -Name "Output exists and is readable" -Status $(if ($valid) { "PASS" } else { "FAIL" }) -Detail "Duration: ${outDuration}s, Size: ${sizeMb}MB"
    }
} else {
    Write-TestResult -Name "Output checks" -Status "SKIP" -Detail "No -OutputPath supplied."
}

Write-Host ""
Write-Host "========================================"
if ($allPassed) {
    Write-Host "Result: ALL REQUIRED CHECKS PASSED" -ForegroundColor Green
    exit 0
}

Write-Host "Result: SOME REQUIRED CHECKS FAILED" -ForegroundColor Red
exit 1
