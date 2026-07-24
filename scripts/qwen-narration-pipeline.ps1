#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [string]$Text,

    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$TextFile,

    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$ReferenceWav,

    [string]$ReferenceText,

    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$ReferenceTextFile,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [string]$TranscriptPrefix,
    [string]$QwenLanguage = "Chinese",
    [string]$WhisperLanguage = "zh",

    [string]$QwenWrapperPath,
    [string]$WhisperWrapperPath,
    [string]$QwenTtsPath = $env:QWENTTS_CPP_EXE,
    [string]$QwenModelPath = $env:QWENTTS_CPP_MODEL,
    [string]$QwenCodecPath = $env:QWENTTS_CPP_CODEC,
    [string]$WhisperCliPath = $env:WHISPER_CPP_EXE,
    [string]$WhisperModelPath = $env:WHISPER_CPP_MODEL,

    [ValidateRange(-1, [int]::MaxValue)]
    [int]$Seed = 42,

    [ValidateRange(1, 16384)]
    [int]$MaxNew = 2048,

    [switch]$Greedy,
    [switch]$Cpu,
    [switch]$Force,
    [switch]$ConfirmVoiceRights,
    [switch]$PassThru
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmVoiceRights) {
    throw "Pass -ConfirmVoiceRights only after confirming the reference voice is yours or explicitly licensed."
}
if ([string]::IsNullOrWhiteSpace($Text) -eq [string]::IsNullOrWhiteSpace($TextFile)) {
    throw "Provide exactly one of -Text or -TextFile."
}
if ([string]::IsNullOrWhiteSpace($ReferenceText) -eq
    [string]::IsNullOrWhiteSpace($ReferenceTextFile)) {
    throw "Provide exactly one of -ReferenceText or -ReferenceTextFile."
}

if ([string]::IsNullOrWhiteSpace($QwenWrapperPath)) {
    $QwenWrapperPath = Join-Path $PSScriptRoot "qwen-voice-clone.ps1"
}
if ([string]::IsNullOrWhiteSpace($WhisperWrapperPath)) {
    $WhisperWrapperPath = Join-Path $PSScriptRoot "whisper-cli.ps1"
}
foreach ($wrapper in @($QwenWrapperPath, $WhisperWrapperPath)) {
    if (-not (Test-Path -LiteralPath $wrapper -PathType Leaf)) {
        throw "Required pipeline wrapper was not found: $wrapper"
    }
}

function Resolve-OutputPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not [IO.Path]::IsPathRooted($Path)) {
        $Path = Join-Path (Get-Location).ProviderPath $Path
    }
    return [IO.Path]::GetFullPath($Path)
}

$OutputPath = Resolve-OutputPath -Path $OutputPath
if ([IO.Path]::GetExtension($OutputPath).ToLowerInvariant() -ne ".wav") {
    throw "OutputPath must use the .wav extension."
}
$outputBase = Join-Path (Split-Path -Parent $OutputPath) (
    [IO.Path]::GetFileNameWithoutExtension($OutputPath)
)
if ([string]::IsNullOrWhiteSpace($TranscriptPrefix)) {
    $TranscriptPrefix = "$outputBase.asr"
} else {
    $TranscriptPrefix = Resolve-OutputPath -Path $TranscriptPrefix
}

$Format = "srt"
$transcriptPath = "$TranscriptPrefix.$Format"
$finalPaths = @($OutputPath, $transcriptPath)
if (@($finalPaths | Select-Object -Unique).Count -ne $finalPaths.Count) {
    throw "Audio and transcript outputs must use different paths."
}

foreach ($path in $finalPaths) {
    if (Test-Path -LiteralPath $path -PathType Container) {
        throw "Output path must be a file, not a directory: $path"
    }
    if ((Test-Path -LiteralPath $path -PathType Leaf) -and -not $Force) {
        throw "Output already exists: $path. Use -Force to preserve existing files as backups."
    }
}

$outputDirectory = Split-Path -Parent $OutputPath
$stagingDirectory = Join-Path $outputDirectory (
    ".qwen-narration-" + [guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Force -Path $stagingDirectory | Out-Null
$stagedAudio = Join-Path $stagingDirectory "narration.wav"
$stagedTranscriptPrefix = Join-Path $stagingDirectory "narration.asr"
$stagedTranscript = "$stagedTranscriptPrefix.$Format"

try {
    $qwenParameters = @{
        ReferenceWav = (Resolve-Path -LiteralPath $ReferenceWav).Path
        OutputPath   = $stagedAudio
        Language     = $QwenLanguage
        Seed         = $Seed
        MaxNew       = $MaxNew
    }
    if ($TextFile) {
        $qwenParameters.TextFile = (Resolve-Path -LiteralPath $TextFile).Path
    } else {
        $qwenParameters.Text = $Text
    }
    if ($ReferenceTextFile) {
        $qwenParameters.ReferenceTextFile =
            (Resolve-Path -LiteralPath $ReferenceTextFile).Path
    } else {
        $qwenParameters.ReferenceText = $ReferenceText
    }
    if (-not [string]::IsNullOrWhiteSpace($QwenTtsPath)) {
        $qwenParameters.QwenTtsPath = $QwenTtsPath
    }
    if (-not [string]::IsNullOrWhiteSpace($QwenModelPath)) {
        $qwenParameters.ModelPath = $QwenModelPath
    }
    if (-not [string]::IsNullOrWhiteSpace($QwenCodecPath)) {
        $qwenParameters.CodecPath = $QwenCodecPath
    }
    if ($Greedy) {
        $qwenParameters.Greedy = $true
    }
    if ($Cpu) {
        $qwenParameters.Cpu = $true
    }

    Write-Host "[1/2] Generating narration with qwentts.cpp..." -ForegroundColor Cyan
    & $QwenWrapperPath @qwenParameters
    if (-not (Test-Path -LiteralPath $stagedAudio -PathType Leaf) -or
        (Get-Item -LiteralPath $stagedAudio).Length -le 0) {
        throw "Qwen narration did not create a non-empty WAV."
    }

    $whisperCommon = @{
        InputPath = $stagedAudio
        Language  = $WhisperLanguage
        Format    = $Format
    }
    if (-not [string]::IsNullOrWhiteSpace($WhisperCliPath)) {
        $whisperCommon.WhisperCliPath = $WhisperCliPath
    }
    if (-not [string]::IsNullOrWhiteSpace($WhisperModelPath)) {
        $whisperCommon.ModelPath = $WhisperModelPath
    }
    if ($Cpu) {
        $whisperCommon.Cpu = $true
    }

    Write-Host "[2/2] Transcribing generated narration with whisper.cpp..." -ForegroundColor Cyan
    $whisperCommon.Task = "transcribe"
    $whisperCommon.OutputPrefix = $stagedTranscriptPrefix
    & $WhisperWrapperPath @whisperCommon
    if (-not (Test-Path -LiteralPath $stagedTranscript -PathType Leaf) -or
        (Get-Item -LiteralPath $stagedTranscript).Length -le 0) {
        throw "Whisper transcription did not create a non-empty output."
    }

} catch {
    throw "Qwen narration pipeline failed. Staging retained at '$stagingDirectory'. $($_.Exception.Message)"
}

$artifacts = @(
    @{ Stage = $stagedAudio; Final = $OutputPath },
    @{ Stage = $stagedTranscript; Final = $transcriptPath }
)
$backups = @{}
$committed = [System.Collections.Generic.List[hashtable]]::new()
$backupStamp = Get-Date -Format "yyyyMMdd-HHmmss"

try {
    foreach ($artifact in $artifacts) {
        $parent = Split-Path -Parent $artifact.Final
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        if (Test-Path -LiteralPath $artifact.Final -PathType Leaf) {
            $backup = "$($artifact.Final).backup-$backupStamp"
            Move-Item -LiteralPath $artifact.Final -Destination $backup
            $backups[$artifact.Final] = $backup
        }
    }
    foreach ($artifact in $artifacts) {
        Move-Item -LiteralPath $artifact.Stage -Destination $artifact.Final
        $committed.Add($artifact)
    }
} catch {
    foreach ($artifact in @($committed)) {
        if (Test-Path -LiteralPath $artifact.Final -PathType Leaf) {
            Move-Item -LiteralPath $artifact.Final -Destination $artifact.Stage
        }
    }
    foreach ($final in @($backups.Keys)) {
        if (-not (Test-Path -LiteralPath $final) -and
            (Test-Path -LiteralPath $backups[$final] -PathType Leaf)) {
            Move-Item -LiteralPath $backups[$final] -Destination $final
        }
    }
    throw
}

if (Test-Path -LiteralPath $stagingDirectory -PathType Container) {
    Remove-Item -LiteralPath $stagingDirectory -Recurse -Force
}

Write-Host "Narration:   $OutputPath" -ForegroundColor Green
Write-Host "Transcript:  $transcriptPath" -ForegroundColor Green
Write-Host "Next: translate the transcript with the active Agent; do not use whisper.cpp --translate." -ForegroundColor Yellow

if ($PassThru) {
    [pscustomobject]@{
        NarrationPath   = $OutputPath
        TranscriptPath  = $transcriptPath
        QwenLanguage    = $QwenLanguage
        WhisperLanguage = $WhisperLanguage
        Format           = $Format
    }
}
