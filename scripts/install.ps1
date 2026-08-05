#Requires -Version 5.1

param(
    [string]$TargetDir = "$env:USERPROFILE\projects\monitor-comunitario",
    [string]$GitName = "Carlos Selva",
    [string]$GitEmail = "selvalabs@users.noreply.github.com",
    [switch]$Force,
    [switch]$SkipPlaywright
)

$ErrorActionPreference = "Stop"

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$SourceRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$TargetDir = [System.IO.Path]::GetFullPath($TargetDir)

Write-Step "Preparing project directory"
Write-Host "Source: $SourceRoot"
Write-Host "Target: $TargetDir"

$projectsDir = Split-Path $TargetDir -Parent
if (-not (Test-Path $projectsDir)) {
    New-Item -ItemType Directory -Path $projectsDir | Out-Null
}

$sourceEqualsTarget = ([System.IO.Path]::GetFullPath($SourceRoot) -eq $TargetDir)

if (-not $sourceEqualsTarget) {
    if ((Test-Path $TargetDir) -and -not $Force) {
        $hasFiles = @(Get-ChildItem -Path $TargetDir -Force -ErrorAction SilentlyContinue).Count -gt 0
        if ($hasFiles) {
            throw "Target folder already exists and is not empty. Use -Force to copy anyway."
        }
    }

    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir | Out-Null
    }

    Write-Step "Copying files to project directory"
    robocopy $SourceRoot $TargetDir /E /XD ".git" ".venv" "__pycache__" ".pytest_cache" ".mypy_cache" ".ruff_cache" /XF ".env" | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Robocopy failed with code $LASTEXITCODE"
    }
}

Set-Location $TargetDir

Write-Step "Checking Python"
if (Test-Command "py") {
    $python = "py -3.12"
} elseif (Test-Command "python") {
    $python = "python"
} else {
    throw "Python not found. Install Python 3.12+ before continuing."
}

Invoke-Expression "$python --version"

Write-Step "Installing/checking uv"
if (-not (Test-Command "uv")) {
    Invoke-Expression "$python -m pip install --user uv"
    $userScripts = Join-Path $env:APPDATA "Python\Python312\Scripts"
    if (Test-Path $userScripts) {
        $env:Path = "$userScripts;$env:Path"
    }
}

uv --version

Write-Step "Installing project dependencies"
uv sync --dev

if (-not $SkipPlaywright) {
    Write-Step "Installing Playwright Chromium"
    uv run playwright install chromium
} else {
    Write-Step "Skipping Playwright Chromium install"
}

if (-not (Test-Path ".env")) {
    Write-Step "Creating .env from .env.example"
    Copy-Item ".env.example" ".env"
}

if (-not (Test-Path ".git")) {
    Write-Step "Initializing local Git repository"
    git init | Out-Null
}

Write-Step "Setting local Git author"
git config user.name $GitName
git config user.email $GitEmail

Write-Step "Install finished"
Write-Host "Project ready at: $TargetDir" -ForegroundColor Green
Write-Host ""
Write-Host "Next commands:"
Write-Host "cd `"$TargetDir`""
Write-Host "uv run uvicorn monitor_comunitario.api.main:app --reload"
Write-Host ""
Write-Host "Use scripts/bootstrap_github.ps1 for non-destructive GitHub setup."
