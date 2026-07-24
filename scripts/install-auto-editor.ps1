#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [string]$Version = "31.3.2",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows) {
    throw "This installer targets Windows. Use the official binary or Homebrew on other platforms."
}
if ($Version -ne "31.3.2") {
    throw "This installer pins verified Auto-Editor 31.3.2. Update asset hashes before changing the version."
}

$architecture = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture
$asset = switch ($architecture) {
    "X64" {
        @{
            Name   = "auto-editor-windows-x86_64.exe"
            Sha256 = "BA508838026D2878F598F6D6CECCEBFB113F9AC784ABD8B2F5F0A07B18BB5674"
        }
    }
    "Arm64" {
        @{
            Name   = "auto-editor-windows-aarch64.exe"
            Sha256 = "5A5DCA5CCD0A7AA8A3423A2F0590235CE70B8319A61EB75E74FDCE2EED6CCE58"
        }
    }
    default {
        throw "Unsupported Windows architecture: $architecture"
    }
}

$installRoot = Join-Path $env:LOCALAPPDATA "auto-editor"
$downloadDirectory = Join-Path $installRoot "downloads"
$binDirectory = Join-Path $installRoot "bin"
$downloadPath = Join-Path $downloadDirectory "$Version-$($asset.Name)"
$installedExe = Join-Path $binDirectory "auto-editor.exe"
$downloadUri = "https://github.com/WyattBlue/auto-editor/releases/download/$Version/$($asset.Name)"

New-Item -ItemType Directory -Force -Path $downloadDirectory, $binDirectory | Out-Null

$downloadRequired = $true
if ((Test-Path -LiteralPath $downloadPath -PathType Leaf) -and -not $Force) {
    $existingHash = (Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash
    if ($existingHash -eq $asset.Sha256) {
        Write-Host "Using verified download: $downloadPath"
        $downloadRequired = $false
    } else {
        throw "Cached download has the wrong SHA256: $downloadPath. Pass -Force to replace it."
    }
}

if ($downloadRequired) {
    $partialPath = "$downloadPath.$([guid]::NewGuid().ToString('N')).partial"
    Invoke-WebRequest -Uri $downloadUri -OutFile $partialPath
    $actualHash = (Get-FileHash -LiteralPath $partialPath -Algorithm SHA256).Hash
    if ($actualHash -ne $asset.Sha256) {
        throw "SHA256 mismatch. Expected $($asset.Sha256), got $actualHash. Partial file: $partialPath"
    }
    Move-Item -LiteralPath $partialPath -Destination $downloadPath -Force
}

if (Test-Path -LiteralPath $installedExe -PathType Leaf) {
    $installedHash = (Get-FileHash -LiteralPath $installedExe -Algorithm SHA256).Hash
    if ($installedHash -ne $asset.Sha256) {
        $backupDirectory = Join-Path $installRoot "backups"
        $backupPath = Join-Path $backupDirectory "auto-editor-$(Get-Date -Format 'yyyyMMdd-HHmmss').exe"
        New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null
        Move-Item -LiteralPath $installedExe -Destination $backupPath
        Write-Host "Previous Auto-Editor moved to: $backupPath" -ForegroundColor Yellow
    }
}

Copy-Item -LiteralPath $downloadPath -Destination $installedExe -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "auto-edit.ps1") -Destination $binDirectory -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "auto-edit.cmd") -Destination $binDirectory -Force

[Environment]::SetEnvironmentVariable("AUTO_EDITOR_EXE", $installedExe, "User")
$env:AUTO_EDITOR_EXE = $installedExe

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @($userPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($binDirectory -notin $pathEntries) {
    [Environment]::SetEnvironmentVariable(
        "Path",
        (($pathEntries + $binDirectory) -join ";").Trim(";"),
        "User"
    )
}
if ($binDirectory -notin ($env:Path -split ";")) {
    $env:Path = "$binDirectory;$env:Path"
}

$versionOutput = @(& $installedExe --version 2>&1)
$versionExitCode = $LASTEXITCODE
$installedVersion = ($versionOutput | Select-Object -First 1).ToString().Trim()
if ($versionExitCode -ne 0 -or $installedVersion -ne $Version) {
    throw "Installed Auto-Editor failed validation. Expected $Version, got '$installedVersion'."
}

$wrapperHelp = & pwsh -NoLogo -NoProfile -File (Join-Path $binDirectory "auto-edit.ps1") -? 2>&1
$wrapperExitCode = $LASTEXITCODE
if ($wrapperExitCode -ne 0 -or ($wrapperHelp -join [Environment]::NewLine) -notmatch "InputPath") {
    throw "Installed auto-edit wrapper failed its help smoke test."
}

Write-Host "Auto-Editor installed globally for the current user." -ForegroundColor Green
Write-Host "Version: $installedVersion"
Write-Host "CLI:     $installedExe"
Write-Host "Wrapper: $(Join-Path $binDirectory 'auto-edit.cmd')"
Write-Host "SHA256:  $($asset.Sha256)"
Write-Host "Open a new terminal and run: auto-editor --version"
Write-Host "Safe preview: auto-edit -InputPath input.mp4 -Mode Preview"
