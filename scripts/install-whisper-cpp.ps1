#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [string]$Version = "v1.9.1",
    [ValidateSet("12.4.0", "11.8.0")]
    [string]$CudaVersion = "12.4.0",
    [string]$Model = "large-v3-turbo",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$installRoot = Join-Path $env:LOCALAPPDATA "whisper.cpp"
$downloadDirectory = Join-Path $installRoot "downloads"
$binDirectory = Join-Path $installRoot "bin"
$cpuBinDirectory = Join-Path $installRoot "cpu-bin"
$modelDirectory = Join-Path $installRoot "models"
$modelPath = Join-Path $modelDirectory "ggml-$Model.bin"

New-Item -ItemType Directory -Force -Path $downloadDirectory, $modelDirectory | Out-Null

function Get-VerifiedDownload {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string]$Sha256
    )

    if ((Test-Path -LiteralPath $Destination) -and -not $Force) {
        $existingHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($existingHash -eq $Sha256) {
            Write-Host "Using verified download: $Destination"
            return
        }
        throw "Existing download has the wrong SHA256: $Destination. Pass -Force to replace it."
    }

    $partialPath = "$Destination.partial"
    if (Test-Path -LiteralPath $partialPath) {
        Remove-Item -LiteralPath $partialPath -Force
    }
    Invoke-WebRequest -Uri $Uri -OutFile $partialPath
    $actualHash = (Get-FileHash -LiteralPath $partialPath -Algorithm SHA256).Hash
    if ($actualHash -ne $Sha256) {
        Remove-Item -LiteralPath $partialPath -Force
        throw "SHA256 mismatch for $Uri. Expected $Sha256, got $actualHash."
    }
    Move-Item -LiteralPath $partialPath -Destination $Destination -Force
}

if ($Version -ne "v1.9.1" -or $CudaVersion -ne "12.4.0" -or $Model -ne "large-v3-turbo") {
    throw "This installer pins the verified v1.9.1 / CUDA 12.4 / large-v3-turbo release. Update its hashes before changing versions."
}

$cudaAsset = "whisper-cublas-$CudaVersion-bin-x64.zip"
$cudaZip = Join-Path $downloadDirectory "$([IO.Path]::GetFileNameWithoutExtension($cudaAsset))-$Version.zip"
$cpuZip = Join-Path $downloadDirectory "whisper-bin-x64-$Version.zip"

Get-VerifiedDownload `
    -Uri "https://github.com/ggml-org/whisper.cpp/releases/download/$Version/$cudaAsset" `
    -Destination $cudaZip `
    -Sha256 "106A2030EFF8998E4EF320FE72E263A78449E9040386EE27C41EA80B001B601B"
Get-VerifiedDownload `
    -Uri "https://github.com/ggml-org/whisper.cpp/releases/download/$Version/whisper-bin-x64.zip" `
    -Destination $cpuZip `
    -Sha256 "7D8BE46ECD31828E1EB7A2ECDD0D6B314FEAFD82163038AB6092594B0A063539"
Get-VerifiedDownload `
    -Uri "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$Model.bin?download=true" `
    -Destination $modelPath `
    -Sha256 "1FC70F774D38EB169993AC391EEA357EF47C88757EF72EE5943879B7E8E2BC69"

$stagingDirectory = Join-Path $installRoot "install-staging"
if (Test-Path -LiteralPath $stagingDirectory) {
    Remove-Item -LiteralPath $stagingDirectory -Recurse -Force
}
$cudaStaging = Join-Path $stagingDirectory "cuda"
$cpuStaging = Join-Path $stagingDirectory "cpu"
New-Item -ItemType Directory -Force -Path $cudaStaging, $cpuStaging | Out-Null

try {
    Expand-Archive -LiteralPath $cudaZip -DestinationPath $cudaStaging -Force
    Expand-Archive -LiteralPath $cpuZip -DestinationPath $cpuStaging -Force
    $cudaCli = Get-ChildItem -LiteralPath $cudaStaging -Recurse -Filter "whisper-cli.exe" | Select-Object -First 1
    $cpuCli = Get-ChildItem -LiteralPath $cpuStaging -Recurse -Filter "whisper-cli.exe" | Select-Object -First 1
    if (-not $cudaCli -or -not $cpuCli) {
        throw "The official archives did not contain whisper-cli.exe."
    }

    if (Test-Path -LiteralPath $binDirectory) {
        Remove-Item -LiteralPath $binDirectory -Recurse -Force
    }
    if (Test-Path -LiteralPath $cpuBinDirectory) {
        Remove-Item -LiteralPath $cpuBinDirectory -Recurse -Force
    }
    Copy-Item -LiteralPath $cudaCli.Directory.FullName -Destination $binDirectory -Recurse
    Copy-Item -LiteralPath $cpuCli.Directory.FullName -Destination $cpuBinDirectory -Recurse
} finally {
    if (Test-Path -LiteralPath $stagingDirectory) {
        Remove-Item -LiteralPath $stagingDirectory -Recurse -Force
    }
}

[Environment]::SetEnvironmentVariable("WHISPER_CPP_MODEL", $modelPath, "User")
[Environment]::SetEnvironmentVariable("WHISPER_CPP_EXE", (Join-Path $binDirectory "whisper-cli.exe"), "User")
$env:WHISPER_CPP_MODEL = $modelPath
$env:WHISPER_CPP_EXE = Join-Path $binDirectory "whisper-cli.exe"

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @($userPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($binDirectory -notin $pathEntries) {
    $newUserPath = (($pathEntries + $binDirectory) -join ";").Trim(";")
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
}
if ($binDirectory -notin ($env:Path -split ";")) {
    $env:Path = "$binDirectory;$env:Path"
}

& (Join-Path $binDirectory "whisper-cli.exe") --version
if ($LASTEXITCODE -ne 0) {
    throw "Installed whisper-cli failed its version smoke test."
}

Write-Host "whisper.cpp installed globally for the current user." -ForegroundColor Green
Write-Host "CLI:   $(Join-Path $binDirectory 'whisper-cli.exe')"
Write-Host "Model: $modelPath"
Write-Host "Open a new terminal and run: whisper-cli --version"
