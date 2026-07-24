#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$dependencies = @(
    @{ Name = "FFmpeg"; Exe = "ffmpeg"; Arguments = @("-version"); Pattern = "ffmpeg version"; Optional = $false },
    @{ Name = "FFprobe"; Exe = "ffprobe"; Arguments = @("-version"); Pattern = "ffprobe version"; Optional = $false },
    @{ Name = "Auto-Editor"; Exe = "auto-editor"; Arguments = @("--version"); Pattern = "auto-editor"; Optional = $true },
    @{ Name = "yt-dlp"; Exe = "yt-dlp"; Arguments = @("--version"); Pattern = "\d"; Optional = $true },
    @{ Name = "whisper.cpp CLI"; Exe = "whisper-cli"; Arguments = @("--version"); Pattern = "whisper|version"; Optional = $true },
    @{ Name = "qwentts.cpp CLI"; Exe = "qwen-tts"; Arguments = @("--help"); Pattern = "qwentts\.cpp|Usage:"; AllowedExitCodes = @(0, 1); Optional = $true },
    @{ Name = "Python 3.8+"; Exe = "python"; Arguments = @("--version"); Pattern = "Python 3\.(?:[89]|[1-9]\d)"; Optional = $true }
)

$requiredPassed = $true
$missingOptional = [System.Collections.Generic.List[string]]::new()

Write-Host "========================================"
Write-Host "YouTube Video Editor - Dependency Check"
Write-Host "========================================"
Write-Host ""

foreach ($dependency in $dependencies) {
    $command = Get-Command $dependency.Exe -ErrorAction SilentlyContinue
    if (-not $command) {
        if ($dependency.Optional) {
            Write-Host "[ SKIP ] $($dependency.Name) - not installed" -ForegroundColor Yellow
            $missingOptional.Add($dependency.Name)
        } else {
            Write-Host "[FAILED] $($dependency.Name) - command not found in PATH" -ForegroundColor Red
            $requiredPassed = $false
        }
        Write-Host ""
        continue
    }

    try {
        $output = & $command.Source @($dependency.Arguments) 2>&1
        $outputText = $output -join [Environment]::NewLine
        $allowedExitCodes = if ($dependency.ContainsKey("AllowedExitCodes")) {
            @($dependency.AllowedExitCodes)
        } else {
            @(0)
        }
        $matched = $LASTEXITCODE -in $allowedExitCodes -and $outputText -match $dependency.Pattern
        if ($matched) {
            Write-Host "[  OK  ] $($dependency.Name)" -ForegroundColor Green
            $firstLine = ($output | Select-Object -First 1).ToString().Trim()
            if ($firstLine.Length -gt 120) {
                $firstLine = $firstLine.Substring(0, 120)
            }
            Write-Host "         $firstLine"
        } elseif ($dependency.Optional) {
            Write-Host "[ WARN ] $($dependency.Name) - command ran but version check failed" -ForegroundColor Yellow
            $missingOptional.Add($dependency.Name)
        } else {
            Write-Host "[FAILED] $($dependency.Name) - version check failed" -ForegroundColor Red
            $requiredPassed = $false
        }
    } catch {
        if ($dependency.Optional) {
            Write-Host "[ WARN ] $($dependency.Name) - $($_.Exception.Message)" -ForegroundColor Yellow
            $missingOptional.Add($dependency.Name)
        } else {
            Write-Host "[FAILED] $($dependency.Name) - $($_.Exception.Message)" -ForegroundColor Red
            $requiredPassed = $false
        }
    }
    Write-Host ""
}

Write-Host "========================================"
if ($requiredPassed) {
    Write-Host "Essential dependencies: ALL OK" -ForegroundColor Green
} else {
    Write-Host "Essential dependencies: SOME MISSING" -ForegroundColor Red
    Write-Host "Install FFmpeg from: https://ffmpeg.org/download.html" -ForegroundColor Cyan
}

if ($missingOptional.Count -gt 0) {
    Write-Host ""
    Write-Host "Optional tools not available:" -ForegroundColor Yellow
    foreach ($tool in $missingOptional) {
        Write-Host "  - $tool" -ForegroundColor Yellow
    }
    Write-Host "Install only the tools needed for the requested workflow." -ForegroundColor Cyan
}

if ($requiredPassed) {
    exit 0
}
exit 1
