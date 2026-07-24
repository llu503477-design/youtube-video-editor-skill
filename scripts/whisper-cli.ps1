#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$InputPath,

    [string]$OutputPrefix,
    [string]$Language = "auto",

    [ValidateSet("transcribe", "translate")]
    [string]$Task = "transcribe",

    [ValidateSet("srt", "vtt", "txt", "json", "csv", "lrc")]
    [string]$Format = "srt",

    [string]$ModelPath = $env:WHISPER_CPP_MODEL,
    [string]$WhisperCliPath = $env:WHISPER_CPP_EXE,

    [ValidateRange(0, 256)]
    [int]$Threads = 0,

    [switch]$Cpu,
    [switch]$Force,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AdditionalArguments
)

$ErrorActionPreference = "Stop"

if ($Task -eq "translate") {
    throw "whisper.cpp translation is disabled for this skill. Transcribe first, then have the active Agent translate the SRT while preserving cue indexes and timestamps."
}
foreach ($argument in $AdditionalArguments) {
    if ($argument -match "^(?i:--translate|-tr)(?:=|$)") {
        throw "whisper.cpp translation flags are disabled for this skill. Transcribe first, then have the active Agent translate the SRT."
    }
}

$installRoot = Join-Path $env:LOCALAPPDATA "whisper.cpp"
$defaultModel = Join-Path $installRoot "models\ggml-large-v3-turbo.bin"
$cpuCli = Join-Path $installRoot "cpu-bin\whisper-cli.exe"
$globalCli = Join-Path $installRoot "bin\whisper-cli.exe"

if ([string]::IsNullOrWhiteSpace($ModelPath)) {
    $ModelPath = $defaultModel
}

if ([string]::IsNullOrWhiteSpace($WhisperCliPath)) {
    if ($Cpu -and (Test-Path -LiteralPath $cpuCli -PathType Leaf)) {
        $WhisperCliPath = $cpuCli
    } else {
        $command = Get-Command "whisper-cli.exe" -ErrorAction SilentlyContinue
        if ($command) {
            $WhisperCliPath = $command.Source
        } elseif (Test-Path -LiteralPath $globalCli -PathType Leaf) {
            $WhisperCliPath = $globalCli
        } elseif (Test-Path -LiteralPath $cpuCli -PathType Leaf) {
            $WhisperCliPath = $cpuCli
        }
    }
}

if ([string]::IsNullOrWhiteSpace($WhisperCliPath) -or
    -not (Test-Path -LiteralPath $WhisperCliPath -PathType Leaf)) {
    throw "whisper-cli.exe was not found. Run scripts/install-whisper-cpp.ps1 first."
}
if (-not (Test-Path -LiteralPath $ModelPath -PathType Leaf)) {
    throw "Whisper model was not found: $ModelPath"
}

$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
if ([string]::IsNullOrWhiteSpace($OutputPrefix)) {
    $inputItem = Get-Item -LiteralPath $resolvedInput
    $OutputPrefix = Join-Path $inputItem.DirectoryName $inputItem.BaseName
} elseif (-not [System.IO.Path]::IsPathRooted($OutputPrefix)) {
    $OutputPrefix = Join-Path (Get-Location).Path $OutputPrefix
}
$OutputPrefix = [System.IO.Path]::GetFullPath($OutputPrefix)

$outputDirectory = Split-Path -Parent $OutputPrefix
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$outputPath = "$OutputPrefix.$Format"
if (Test-Path -LiteralPath $outputPath -PathType Container) {
    throw "Output path must be a file, not a directory: $outputPath"
}
if ((Test-Path -LiteralPath $outputPath) -and -not $Force) {
    throw "Output already exists: $outputPath. Pass -Force only when overwrite is intended."
}

$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) (
    "youtube-video-editor-whisper-" + [guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $temporaryDirectory | Out-Null
$audioPath = $resolvedInput
$nativeAudioExtensions = @(".flac", ".mp3", ".ogg", ".wav")
$stagedOutputPrefix = Join-Path $temporaryDirectory "transcript"
$stagedOutputPath = "$stagedOutputPrefix.$Format"

try {
    if ([System.IO.Path]::GetExtension($resolvedInput).ToLowerInvariant() -notin $nativeAudioExtensions) {
        $ffmpeg = Get-Command "ffmpeg.exe" -ErrorAction SilentlyContinue
        if (-not $ffmpeg) {
            throw "FFmpeg is required to extract audio from this input format."
        }

        $audioPath = Join-Path $temporaryDirectory "audio.wav"
        & $ffmpeg.Source -hide_banner -loglevel error -i $resolvedInput -vn -acodec pcm_s16le -ar 16000 -ac 1 -y $audioPath
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $audioPath -PathType Leaf)) {
            throw "FFmpeg audio extraction failed with exit code $LASTEXITCODE."
        }
    }

    $arguments = @(
        "--model", $ModelPath,
        "--file", $audioPath,
        "--language", $Language,
        "--output-$Format",
        "--output-file", $stagedOutputPrefix
    )
    if ($Threads -gt 0) {
        $arguments += @("--threads", $Threads)
    }
    if ($Cpu) {
        $arguments += "--no-gpu"
    }
    if ($AdditionalArguments) {
        $arguments += $AdditionalArguments
    }

    $global:LASTEXITCODE = 0
    & $WhisperCliPath @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "whisper-cli failed with exit code $LASTEXITCODE."
    }
    if (-not (Test-Path -LiteralPath $stagedOutputPath -PathType Leaf)) {
        throw "whisper-cli completed but did not create the expected staged output: $stagedOutputPath"
    }
    if ((Get-Item -LiteralPath $stagedOutputPath).Length -le 0) {
        throw "whisper-cli created an empty staged output: $stagedOutputPath"
    }

    $backupPath = $null
    try {
        if (Test-Path -LiteralPath $outputPath -PathType Leaf) {
            $backupPath = "$outputPath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
            Move-Item -LiteralPath $outputPath -Destination $backupPath
        }
        Move-Item -LiteralPath $stagedOutputPath -Destination $outputPath
        if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf) -or
            (Get-Item -LiteralPath $outputPath).Length -le 0) {
            throw "Failed to publish a non-empty Whisper output: $outputPath"
        }
    } catch {
        if ($backupPath -and
            (Test-Path -LiteralPath $backupPath -PathType Leaf) -and
            -not (Test-Path -LiteralPath $outputPath)) {
            Move-Item -LiteralPath $backupPath -Destination $outputPath
        }
        throw
    }

    Write-Host "Whisper output: $outputPath" -ForegroundColor Green
    if ($backupPath) {
        Write-Host "Previous output backup: $backupPath" -ForegroundColor Yellow
    }
} finally {
    if ($temporaryDirectory -and (Test-Path -LiteralPath $temporaryDirectory)) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
