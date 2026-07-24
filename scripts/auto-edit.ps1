#!/usr/bin/env pwsh
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [Alias("Input")]
    [string]$InputPath,

    [Alias("Output")]
    [string]$OutputPath,

    [ValidateSet("Preview", "Render", "Export")]
    [string]$Mode = "Preview",

    [ValidateSet("Conservative", "Balanced", "Aggressive", "Podcast", "Motion", "FastReview")]
    [string]$Profile = "Balanced",

    [string]$EditExpression,
    [string]$Margin,
    [string]$Smooth,
    [string]$InactiveAction,
    [string]$Transition,

    [ValidateSet("premiere", "premiere-otio", "resolve", "final-cut-pro", "shotcut", "kdenlive", "v3")]
    [string]$ExportFormat = "premiere-otio",

    [ValidateSet("none", "ebu", "peak")]
    [string]$AudioNormalize = "none",

    [ValidateRange(0, 63)]
    [int]$Crf = 23,

    [string]$AutoEditorPath,
    [switch]$NoCache,
    [switch]$Force,
    [switch]$PassThru
)

$ErrorActionPreference = "Stop"

$profiles = @{
    Conservative = @{
        Edit     = "audio:-34dB"
        Margin   = "0.35sec,0.50sec"
        Smooth   = "0.40sec,0.15sec"
        Inactive = "cut"
    }
    Balanced = @{
        Edit     = "audio:-28dB"
        Margin   = "0.25sec,0.35sec"
        Smooth   = "0.25sec,0.10sec"
        Inactive = "cut"
    }
    Aggressive = @{
        Edit     = "audio:-20dB"
        Margin   = "0.12sec,0.18sec"
        Smooth   = "0.15sec,0.08sec"
        Inactive = "cut"
    }
    Podcast = @{
        Edit     = "audio:-32dB"
        Margin   = "0.40sec,0.60sec"
        Smooth   = "0.50sec,0.20sec"
        Inactive = "cut"
    }
    Motion = @{
        Edit     = "motion:threshold=2%"
        Margin   = "0.20sec,0.30sec"
        Smooth   = "0.25sec,0.10sec"
        Inactive = "cut"
    }
    FastReview = @{
        Edit     = "audio:-28dB"
        Margin   = "0.20sec,0.25sec"
        Smooth   = "0.25sec,0.10sec"
        Inactive = "speed:8"
    }
}

function Assert-SafeValue {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [AllowEmptyString()][string]$Value
    )

    if ($Value -match "[`r`n`0]") {
        throw "$Name must not contain control characters."
    }
}

function Resolve-AutoEditor {
    if (-not [string]::IsNullOrWhiteSpace($AutoEditorPath)) {
        if (-not (Test-Path -LiteralPath $AutoEditorPath -PathType Leaf)) {
            throw "Auto-Editor executable was not found: $AutoEditorPath"
        }
        return (Resolve-Path -LiteralPath $AutoEditorPath).Path
    }

    $siblingExecutable = Join-Path $PSScriptRoot "auto-editor.exe"
    if (Test-Path -LiteralPath $siblingExecutable -PathType Leaf) {
        return $siblingExecutable
    }

    if (-not [string]::IsNullOrWhiteSpace($env:AUTO_EDITOR_EXE) -and
        (Test-Path -LiteralPath $env:AUTO_EDITOR_EXE -PathType Leaf)) {
        return (Resolve-Path -LiteralPath $env:AUTO_EDITOR_EXE).Path
    }

    $command = Get-Command "auto-editor" -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "auto-editor was not found. Run scripts/install-auto-editor.ps1 first."
    }
    return $command.Source
}

function Format-CommandArgument {
    param([string]$Value)

    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + $Value.Replace('"', '\"') + '"'
}

function Get-ExportExtension {
    param([string]$Format)

    return @{
        premiere       = ".xml"
        "premiere-otio" = ".otio"
        resolve        = ".fcpxml"
        "final-cut-pro" = ".fcpxml"
        shotcut        = ".mlt"
        kdenlive       = ".kdenlive"
        v3             = ".v3"
    }[$Format]
}

$isUrl = $InputPath -match "^https?://"
if ($isUrl) {
    $resolvedInput = $InputPath
} else {
    if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
        throw "Input file was not found: $InputPath"
    }
    $resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
}

$selected = $profiles[$Profile]
$effectiveEdit = if ($EditExpression) { $EditExpression } else { $selected.Edit }
$effectiveMargin = if ($Margin) { $Margin } else { $selected.Margin }
$effectiveSmooth = if ($Smooth) { $Smooth } else { $selected.Smooth }
$effectiveInactive = if ($InactiveAction) { $InactiveAction } else { $selected.Inactive }

Assert-SafeValue -Name "EditExpression" -Value $effectiveEdit
Assert-SafeValue -Name "Margin" -Value $effectiveMargin
Assert-SafeValue -Name "Smooth" -Value $effectiveSmooth
Assert-SafeValue -Name "InactiveAction" -Value $effectiveInactive
if ($Transition) {
    Assert-SafeValue -Name "Transition" -Value $Transition
}

$resolvedOutput = $null
$outputDirectory = $null
$backupPath = $null
$stagingOutput = $null
if ($Mode -ne "Preview") {
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        if ($isUrl) {
            throw "-OutputPath is required for URL inputs."
        }
        if ($Mode -eq "Export") {
            throw "-OutputPath is required in Export mode."
        }

        $inputItem = Get-Item -LiteralPath $resolvedInput
        $resolvedOutput = Join-Path $inputItem.DirectoryName (
            $inputItem.BaseName + ".auto-edited" + $inputItem.Extension
        )
    } else {
        $resolvedOutput = [IO.Path]::GetFullPath(
            $OutputPath,
            (Get-Location).ProviderPath
        )
    }

    if (-not $isUrl -and $resolvedOutput -eq $resolvedInput) {
        throw "OutputPath must be different from InputPath."
    }

    $outputExtension = [IO.Path]::GetExtension($resolvedOutput)
    if ([string]::IsNullOrWhiteSpace($outputExtension)) {
        throw "OutputPath must include a file extension."
    }
    if ($Mode -eq "Export") {
        $requiredExtension = Get-ExportExtension -Format $ExportFormat
        if ($outputExtension -ne $requiredExtension) {
            throw "Export format '$ExportFormat' requires an '$requiredExtension' OutputPath."
        }
    }

    $outputDirectory = Split-Path -Parent $resolvedOutput
    $outputBaseName = [IO.Path]::GetFileNameWithoutExtension($resolvedOutput)
    $stagingOutput = Join-Path $outputDirectory (
        ".$outputBaseName.auto-editor-$([guid]::NewGuid().ToString('N')).partial$outputExtension"
    )

    if (Test-Path -LiteralPath $resolvedOutput -PathType Container) {
        throw "OutputPath must be a file, not a directory: $resolvedOutput"
    }
    if (Test-Path -LiteralPath $resolvedOutput -PathType Leaf) {
        if (-not $Force) {
            throw "Output already exists: $resolvedOutput. Use -Force to preserve it as a timestamped backup."
        }
    }
}

$cli = Resolve-AutoEditor
$arguments = [System.Collections.Generic.List[string]]::new()
$arguments.Add($resolvedInput)
$arguments.Add("--edit")
$arguments.Add($effectiveEdit)
$arguments.Add("--margin")
$arguments.Add($effectiveMargin)
$arguments.Add("--smooth")
$arguments.Add($effectiveSmooth)
$arguments.Add("-w:0")
$arguments.Add($effectiveInactive)
$arguments.Add("--no-open")

if ($Transition) {
    $arguments.Add("--transition")
    $arguments.Add($Transition)
}
if ($AudioNormalize -ne "none") {
    $arguments.Add("--audio-normalize")
    $arguments.Add($AudioNormalize)
}
if ($NoCache) {
    $arguments.Add("--no-cache")
}

switch ($Mode) {
    "Preview" {
        $arguments.Add("--preview")
    }
    "Render" {
        $arguments.Add("-crf")
        $arguments.Add($Crf.ToString([Globalization.CultureInfo]::InvariantCulture))
        $arguments.Add("-o")
        $arguments.Add($stagingOutput)
    }
    "Export" {
        $arguments.Add("--export")
        $arguments.Add($ExportFormat)
        $arguments.Add("-o")
        $arguments.Add($stagingOutput)
    }
}

$displayCommand = ((@($cli) + $arguments) | ForEach-Object {
    Format-CommandArgument -Value $_
}) -join " "
Write-Host "Auto-Editor profile: $Profile ($Mode)" -ForegroundColor Cyan
Write-Host "Command: $displayCommand"

$shouldProcessTarget = if ($Mode -eq "Preview") { $resolvedInput } else { $resolvedOutput }
if (-not $PSCmdlet.ShouldProcess($shouldProcessTarget, "Run Auto-Editor in $Mode mode")) {
    return
}

if ($Mode -ne "Preview") {
    if (-not [string]::IsNullOrWhiteSpace($outputDirectory)) {
        New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
    }
}

$commandOutput = & $cli @arguments 2>&1
$invocationSucceeded = $?
$nativeExitCode = $LASTEXITCODE
$exitCode = if ($null -eq $nativeExitCode) {
    if ($invocationSucceeded) { 0 } else { 1 }
} else {
    $nativeExitCode
}
$commandOutput | Write-Output
if ($exitCode -ne 0) {
    $partialDetail = if ($Mode -ne "Preview" -and
        $stagingOutput -and
        (Test-Path -LiteralPath $stagingOutput -PathType Leaf)) {
        " Partial output retained at: $stagingOutput"
    } else {
        ""
    }
    throw "auto-editor failed with exit code $exitCode.$partialDetail"
}

if ($Mode -ne "Preview") {
    if (-not (Test-Path -LiteralPath $stagingOutput -PathType Leaf)) {
        throw "auto-editor reported success but did not create: $stagingOutput"
    }
    if ((Get-Item -LiteralPath $stagingOutput).Length -le 0) {
        throw "auto-editor created an empty output: $stagingOutput"
    }
    if (Test-Path -LiteralPath $resolvedOutput -PathType Container) {
        throw "OutputPath became a directory while rendering: $resolvedOutput"
    }

    try {
        if (Test-Path -LiteralPath $resolvedOutput -PathType Leaf) {
            if (-not $Force) {
                throw "Output appeared while rendering and was not replaced: $resolvedOutput"
            }
            $backupPath = "$resolvedOutput.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Move-Item -LiteralPath $resolvedOutput -Destination $backupPath
            Write-Host "Existing output moved to: $backupPath" -ForegroundColor Yellow
        }
        Move-Item -LiteralPath $stagingOutput -Destination $resolvedOutput
    } catch {
        if ($backupPath -and
            (Test-Path -LiteralPath $backupPath -PathType Leaf) -and
            -not (Test-Path -LiteralPath $resolvedOutput)) {
            Move-Item -LiteralPath $backupPath -Destination $resolvedOutput
        }
        throw
    }
    Write-Host "Output: $resolvedOutput" -ForegroundColor Green
}

if ($PassThru) {
    [pscustomobject]@{
        Mode           = $Mode
        Profile        = $Profile
        InputPath      = $resolvedInput
        OutputPath     = $resolvedOutput
        EditExpression = $effectiveEdit
        Margin         = $effectiveMargin
        Smooth         = $effectiveSmooth
        InactiveAction = $effectiveInactive
        ExitCode       = $exitCode
    }
}
