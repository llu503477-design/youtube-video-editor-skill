#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("plan", "ass", "validate", "render")]
    [string]$Command,

    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [string]$PlanPath,

    [string]$AssPath,

    [int]$Width = 1080,
    [int]$Height = 1920,
    [double]$Fps = 30,
    [string]$Language = "zh-TW",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python was not found in PATH."
}

switch ($Command) {
    "plan" {
        $args = @(
            (Join-Path $scriptRoot "typography_plan.py"),
            $InputPath,
            $OutputPath,
            "--width", $Width,
            "--height", $Height,
            "--fps", $Fps,
            "--language", $Language
        )
        if ($Force) { $args += "--force" }
        & $python.Source @args
    }
    "ass" {
        $args = @(
            (Join-Path $scriptRoot "generate_dynamic_ass.py"),
            $InputPath,
            $OutputPath
        )
        if ($Force) { $args += "--force" }
        & $python.Source @args
    }
    "validate" {
        $args = @(
            (Join-Path $scriptRoot "validate_typography_project.py"),
            $InputPath,
            "--report", $OutputPath
        )
        if ($Force) { $args += "--force" }
        & $python.Source @args
    }
    "render" {
        if ([string]::IsNullOrWhiteSpace($PlanPath)) {
            throw "-PlanPath is required for render."
        }
        $args = @{
            InputVideo = $InputPath
            PlanPath = $PlanPath
            OutputVideo = $OutputPath
        }
        if (-not [string]::IsNullOrWhiteSpace($AssPath)) {
            $args.AssPath = $AssPath
        }
        if ($Force) { $args.Force = $true }
        & (Join-Path $scriptRoot "render-typography.ps1") @args
    }
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
