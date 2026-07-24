#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [string]$Commit = "82cd05b9f3a175612dc89fd6943e610fab096ef5",
    [string]$CudaRoot = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2",
    [switch]$ForceBuild,
    [switch]$ForceDownload
)

$ErrorActionPreference = "Stop"

$expectedCommit = "82cd05b9f3a175612dc89fd6943e610fab096ef5"
if ($Commit -ne $expectedCommit) {
    throw "This installer pins verified commit $expectedCommit. Update the build and model validation before changing it."
}

$installRoot = Join-Path $env:LOCALAPPDATA "qwentts.cpp"
$sourceDirectory = Join-Path $installRoot "src\$Commit"
$buildDirectory = Join-Path $installRoot "build\$Commit-cuda132-sm86"
$binDirectory = Join-Path $installRoot "bin"
$modelDirectory = Join-Path $installRoot "models"
$talkerPath = Join-Path $modelDirectory "qwen-talker-1.7b-base-Q8_0.gguf"
$codecPath = Join-Path $modelDirectory "qwen-tokenizer-12hz-Q8_0.gguf"
$vcvars = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

foreach ($required in @(
    (Get-Command "git.exe" -ErrorAction SilentlyContinue).Source,
    (Get-Command "cmake.exe" -ErrorAction SilentlyContinue).Source,
    (Get-Command "ninja.exe" -ErrorAction SilentlyContinue).Source,
    $vcvars,
    (Join-Path $CudaRoot "bin\nvcc.exe")
)) {
    if ([string]::IsNullOrWhiteSpace($required) -or -not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required build tool was not found: $required"
    }
}

New-Item -ItemType Directory -Force -Path $installRoot, $modelDirectory | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $sourceDirectory ".git") -PathType Container)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $sourceDirectory) | Out-Null
    git clone --recurse-submodules https://github.com/ServeurpersoCom/qwentts.cpp.git $sourceDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to clone qwentts.cpp."
    }
    git -C $sourceDirectory checkout --detach $Commit
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to check out qwentts.cpp commit $Commit."
    }
}

$actualCommit = (git -C $sourceDirectory rev-parse HEAD).Trim()
if ($actualCommit -ne $Commit) {
    throw "Existing source is at $actualCommit; expected $Commit."
}
git -C $sourceDirectory submodule update --init --recursive
if ($LASTEXITCODE -ne 0) {
    throw "Failed to initialize qwentts.cpp submodules."
}

$builtCli = Join-Path $buildDirectory "qwen-tts.exe"
if ($ForceBuild -or -not (Test-Path -LiteralPath $builtCli -PathType Leaf)) {
    New-Item -ItemType Directory -Force -Path $buildDirectory | Out-Null
    $configure = 'call "{0}" && set "CUDA_PATH={1}" && set "CUDA_PATH_V13_2={1}" && cmake -S "{2}" -B "{3}" -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DCUDAToolkit_ROOT="{1}" -DCMAKE_CUDA_COMPILER="{1}\bin\nvcc.exe" -DCMAKE_CUDA_FLAGS:STRING="-Xcompiler=/utf-8"' -f $vcvars, $CudaRoot, $sourceDirectory, $buildDirectory
    cmd.exe /d /s /c $configure
    if ($LASTEXITCODE -ne 0) {
        throw "qwentts.cpp CMake configuration failed."
    }

    $build = 'call "{0}" && cmake --build "{1}" --parallel 12' -f $vcvars, $buildDirectory
    cmd.exe /d /s /c $build
    if ($LASTEXITCODE -ne 0) {
        throw "qwentts.cpp CUDA build failed."
    }
}

function Get-VerifiedModel {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string]$Sha256
    )

    if ((Test-Path -LiteralPath $Destination -PathType Leaf) -and -not $ForceDownload) {
        $existingHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($existingHash -eq $Sha256) {
            Write-Host "Using verified model: $Destination"
            return
        }
        throw "Existing model has the wrong SHA256: $Destination. Pass -ForceDownload to replace it."
    }

    $partialPath = "$Destination.$([guid]::NewGuid().ToString('N')).partial"
    Invoke-WebRequest -Uri $Uri -OutFile $partialPath
    $actualHash = (Get-FileHash -LiteralPath $partialPath -Algorithm SHA256).Hash
    if ($actualHash -ne $Sha256) {
        throw "Model SHA256 mismatch. Expected $Sha256, got $actualHash. Partial file: $partialPath"
    }
    Move-Item -LiteralPath $partialPath -Destination $Destination -Force
}

Get-VerifiedModel `
    -Uri "https://huggingface.co/Serveurperso/Qwen3-TTS-GGUF/resolve/main/qwen-talker-1.7b-base-Q8_0.gguf?download=true" `
    -Destination $talkerPath `
    -Sha256 "4B9A33A236908DD9435A42F7A396E38038329D053B704342A6413C08544C4FDA"
Get-VerifiedModel `
    -Uri "https://huggingface.co/Serveurperso/Qwen3-TTS-GGUF/resolve/main/qwen-tokenizer-12hz-Q8_0.gguf?download=true" `
    -Destination $codecPath `
    -Sha256 "1883BEEED99348FC35E23DD225E9082F93F6F8C109330A33D935BAA8ACDBFD94"

if (Test-Path -LiteralPath $binDirectory -PathType Container) {
    $backupDirectory = Join-Path $installRoot ("backups\bin-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backupDirectory) | Out-Null
    Move-Item -LiteralPath $binDirectory -Destination $backupDirectory
    Write-Host "Previous runtime moved to: $backupDirectory"
}
New-Item -ItemType Directory -Path $binDirectory | Out-Null

Get-ChildItem -LiteralPath $buildDirectory -File |
    Where-Object { $_.Extension -in @(".exe", ".dll") } |
    Copy-Item -Destination $binDirectory

$cudaBinDirectory = Join-Path $CudaRoot "bin\x64"
foreach ($pattern in @(
    "cublas64_13.dll",
    "cublasLt64_13.dll"
)) {
    Get-ChildItem -LiteralPath $cudaBinDirectory -Filter $pattern -File -ErrorAction SilentlyContinue |
        Copy-Item -Destination $binDirectory
}

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "qwen-voice-clone.ps1") -Destination $binDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "qwen-voice-clone.cmd") -Destination $binDirectory
[System.IO.File]::WriteAllText(
    (Join-Path $binDirectory ".source-commit"),
    "$Commit`n",
    [System.Text.UTF8Encoding]::new($false)
)

$installedExe = Join-Path $binDirectory "qwen-tts.exe"
[Environment]::SetEnvironmentVariable("QWENTTS_CPP_EXE", $installedExe, "User")
[Environment]::SetEnvironmentVariable("QWENTTS_CPP_MODEL", $talkerPath, "User")
[Environment]::SetEnvironmentVariable("QWENTTS_CPP_CODEC", $codecPath, "User")
[Environment]::SetEnvironmentVariable("QWENTTS_CPP_SOURCE_COMMIT", $Commit, "User")
$env:QWENTTS_CPP_EXE = $installedExe
$env:QWENTTS_CPP_MODEL = $talkerPath
$env:QWENTTS_CPP_CODEC = $codecPath
$env:QWENTTS_CPP_SOURCE_COMMIT = $Commit

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @($userPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($binDirectory -notin $pathEntries) {
    [Environment]::SetEnvironmentVariable("Path", (($pathEntries + $binDirectory) -join ";").Trim(";"), "User")
}
if ($binDirectory -notin ($env:Path -split ";")) {
    $env:Path = "$binDirectory;$env:Path"
}

$helpOutput = & $installedExe --help 2>&1
$helpText = $helpOutput -join [Environment]::NewLine
if ($LASTEXITCODE -notin @(0, 1) -or $helpText -notmatch "(?s)qwentts\.cpp.+Usage:") {
    throw "Installed qwen-tts failed its CLI smoke test."
}
Write-Host ($helpOutput | Select-Object -First 1)

Write-Host "qwentts.cpp installed globally for the current user." -ForegroundColor Green
Write-Host "CLI:    $installedExe"
Write-Host "Talker: $talkerPath"
Write-Host "Codec:  $codecPath"
Write-Host "Open a new terminal and run: qwen-tts --help"
