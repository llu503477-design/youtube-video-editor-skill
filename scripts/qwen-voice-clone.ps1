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

    [string]$Language = "Chinese",
    [string]$ModelPath = $env:QWENTTS_CPP_MODEL,
    [string]$CodecPath = $env:QWENTTS_CPP_CODEC,
    [string]$QwenTtsPath = $env:QWENTTS_CPP_EXE,

    [ValidateRange(-1, [int]::MaxValue)]
    [int]$Seed = 42,

    [ValidateRange(1, 16384)]
    [int]$MaxNew = 2048,

    [switch]$Greedy,
    [switch]$Cpu,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$installRoot = Join-Path $env:LOCALAPPDATA "qwentts.cpp"

if ([string]::IsNullOrWhiteSpace($Text) -eq [string]::IsNullOrWhiteSpace($TextFile)) {
    throw "Provide exactly one of -Text or -TextFile."
}
if (-not [string]::IsNullOrWhiteSpace($ReferenceText) -and
    -not [string]::IsNullOrWhiteSpace($ReferenceTextFile)) {
    throw "Provide at most one of -ReferenceText or -ReferenceTextFile."
}

if ([string]::IsNullOrWhiteSpace($ModelPath)) {
    $ModelPath = Join-Path $installRoot "models\qwen-talker-1.7b-base-Q8_0.gguf"
}
if ([string]::IsNullOrWhiteSpace($CodecPath)) {
    $CodecPath = Join-Path $installRoot "models\qwen-tokenizer-12hz-Q8_0.gguf"
}
if ([string]::IsNullOrWhiteSpace($QwenTtsPath)) {
    $command = Get-Command "qwen-tts.exe" -ErrorAction SilentlyContinue
    if ($command) {
        $QwenTtsPath = $command.Source
    } else {
        $QwenTtsPath = Join-Path $installRoot "bin\qwen-tts.exe"
    }
}

foreach ($requiredFile in @($QwenTtsPath, $ModelPath, $CodecPath)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required qwentts.cpp file was not found: $requiredFile"
    }
}

$targetText = if ($TextFile) {
    Get-Content -LiteralPath $TextFile -Raw -Encoding UTF8
} else {
    $Text
}
if ([string]::IsNullOrWhiteSpace($targetText)) {
    throw "Target text is empty."
}

if (-not [System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath = Join-Path (Get-Location).Path $OutputPath
}
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}
if ((Test-Path -LiteralPath $OutputPath) -and -not $Force) {
    throw "Output already exists: $OutputPath. Pass -Force only when overwrite is intended."
}
if ($Force -and (Test-Path -LiteralPath $OutputPath)) {
    Remove-Item -LiteralPath $OutputPath -Force
}

$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("youtube-video-editor-qwentts-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temporaryDirectory | Out-Null

try {
    $normalizedReference = Join-Path $temporaryDirectory "reference-24k-mono.wav"
    $ffmpeg = Get-Command "ffmpeg.exe" -ErrorAction SilentlyContinue
    if ($ffmpeg) {
        & $ffmpeg.Source -hide_banner -loglevel error -i (Resolve-Path -LiteralPath $ReferenceWav).Path `
            -vn -acodec pcm_s16le -ar 24000 -ac 1 -y $normalizedReference
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $normalizedReference -PathType Leaf)) {
            throw "FFmpeg failed to normalize the reference WAV."
        }
    } else {
        $normalizedReference = (Resolve-Path -LiteralPath $ReferenceWav).Path
    }

    $arguments = @(
        "--model", (Resolve-Path -LiteralPath $ModelPath).Path,
        "--codec", (Resolve-Path -LiteralPath $CodecPath).Path,
        "--ref-wav", $normalizedReference,
        "--lang", $Language,
        "--seed", $Seed.ToString([Globalization.CultureInfo]::InvariantCulture),
        "--max-new", $MaxNew.ToString([Globalization.CultureInfo]::InvariantCulture),
        "--format", "wav16",
        "-o", $OutputPath
    )

    if ($ReferenceTextFile) {
        $arguments += @("--ref-text", (Resolve-Path -LiteralPath $ReferenceTextFile).Path)
    } elseif (-not [string]::IsNullOrWhiteSpace($ReferenceText)) {
        $temporaryReferenceText = Join-Path $temporaryDirectory "reference.txt"
        [System.IO.File]::WriteAllText(
            $temporaryReferenceText,
            $ReferenceText,
            [System.Text.UTF8Encoding]::new($false)
        )
        $arguments += @("--ref-text", $temporaryReferenceText)
    }
    if ($Greedy) {
        $arguments += "--greedy"
    }

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $QwenTtsPath
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.StandardInputEncoding = [System.Text.UTF8Encoding]::new($false)
    foreach ($argument in $arguments) {
        [void]$startInfo.ArgumentList.Add([string]$argument)
    }
    if ($Cpu) {
        $startInfo.Environment["GGML_BACKEND"] = "CPU"
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    if (-not $process.Start()) {
        throw "Failed to start qwen-tts."
    }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.StandardInput.Write($targetText)
    $process.StandardInput.Close()
    $process.WaitForExit()
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()

    if (-not [string]::IsNullOrWhiteSpace($stdout)) {
        Write-Host $stdout.TrimEnd()
    }
    if (-not [string]::IsNullOrWhiteSpace($stderr)) {
        Write-Host $stderr.TrimEnd()
    }
    if ($process.ExitCode -ne 0) {
        throw "qwen-tts failed with exit code $($process.ExitCode)."
    }
    if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        throw "qwen-tts completed but did not create the expected WAV: $OutputPath"
    }

    $probe = Get-Command "ffprobe.exe" -ErrorAction SilentlyContinue
    if ($probe) {
        & $probe.Source -v error -show_entries "stream=codec_name,sample_rate,channels" `
            -show_entries "format=duration" -of json $OutputPath
        if ($LASTEXITCODE -ne 0) {
            throw "The generated WAV failed FFprobe validation."
        }
    }
    Write-Host "Voice clone output: $OutputPath" -ForegroundColor Green
} finally {
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
