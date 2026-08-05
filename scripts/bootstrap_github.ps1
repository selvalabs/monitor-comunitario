#Requires -Version 5.1

param(
    [string]$RepoName = "monitor-comunitario",
    [string]$Description = "Monitor publico de desligamentos programados da Celesc com alertas por endereco.",
    [string]$GitName = "Carlos Selva",
    [string]$GitEmail = "selvalabs@users.noreply.github.com",
    [switch]$Private,
    [switch]$FreshGit,
    [switch]$DeleteExistingRemote
)

$ErrorActionPreference = "Stop"

# Force UTF-8 in the PowerShell session. This avoids mojibake in logs and git output.
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

function Get-GitHubOwner {
    try {
        return (gh api user --jq ".login").Trim()
    } catch {
        throw "Could not detect GitHub owner. Run 'gh auth login' first."
    }
}

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not (Test-Command "gh")) {
    throw "GitHub CLI not found. Install it from https://cli.github.com/ and run gh auth login."
}

if (-not (Test-Command "git")) {
    throw "Git not found."
}

Write-Step "Checking GitHub CLI authentication"
gh auth status

$owner = Get-GitHubOwner
$repoFullName = "$owner/$RepoName"

if ($FreshGit -and (Test-Path ".git")) {
    Write-Step "Removing local .git history to avoid old contributors/authors"
    Remove-Item ".git" -Recurse -Force
}

if ($DeleteExistingRemote) {
    Write-Step "Deleting existing GitHub repository if it exists: $repoFullName"
    Write-Host "If this fails because of missing permission, run:"
    Write-Host "gh auth refresh -s delete_repo"
    try {
        gh repo delete $repoFullName --yes
    } catch {
        Write-Host "Repository may not exist or delete permission is missing. Continuing..." -ForegroundColor Yellow
    }
}

if (-not (Test-Path ".git")) {
    Write-Step "Initializing local git repository"
    git init | Out-Null
}

Write-Step "Setting local git author"
git config user.name $GitName
git config user.email $GitEmail

$currentBranch = git branch --show-current
if ([string]::IsNullOrWhiteSpace($currentBranch)) {
    git checkout -b main
} elseif ($currentBranch -ne "main") {
    git branch -M main
}

# Remove origin if it points to an old repository. gh repo create will add it again.
$existingOrigin = git remote get-url origin 2>$null
if (-not [string]::IsNullOrWhiteSpace($existingOrigin)) {
    Write-Step "Removing existing origin remote"
    git remote remove origin
}

Write-Step "Creating clean initial commit"
git add .

$status = git status --porcelain
if (-not [string]::IsNullOrWhiteSpace($status)) {
    git commit --author "$GitName <$GitEmail>" -m "chore: bootstrap Monitor Comunitario project"
} else {
    Write-Host "Nothing new to commit."
}

$visibility = "--public"
if ($Private) {
    $visibility = "--private"
}

Write-Step "Creating GitHub repository with gh CLI"
gh repo create $RepoName $visibility --source=. --remote=origin --description $Description --push

Write-Step "Done"
gh repo view --web
