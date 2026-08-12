#Requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Commit,
    [string]$OutputDirectory = "artifacts\releases"
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed: $($output -join "`n")"
    }
    return $output
}

function Assert-TrackedTreeSafe {
    param([Parameter(Mandatory = $true)][string]$Revision)
    $paths = @(Invoke-Git @("ls-tree", "-r", "--name-only", $Revision))
    $unsafe = @($paths | Where-Object {
        $protected = $_ -match '(^|/)(\.env($|\.)|credentials\.json$|tunnel-secrets/|snapshots/|data/)'
        $allowedPlaceholder = $_ -match '(^|/)(\.env\.(example|docker\.example|production\.example|supabase\.example)|data/\.gitkeep|snapshots/\.gitkeep)$'
        $protected -and -not $allowedPlaceholder
    })
    if ($unsafe.Count -gt 0) {
        throw "Tracked release contains protected paths: $($unsafe -join ', ')"
    }
}

function Assert-CleanWorktree {
    $status = @(Invoke-Git @("status", "--porcelain", "--untracked-files=all"))
    if ($status.Count -gt 0) {
        throw "Working tree must be clean before preparing a release."
    }
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot
Assert-CleanWorktree
$resolvedCommit = (Invoke-Git @("rev-parse", "--verify", "$Commit^{commit}") | Select-Object -First 1).Trim()
Assert-TrackedTreeSafe -Revision $resolvedCommit

$outputRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputDirectory))
$releaseRoot = Join-Path $outputRoot $resolvedCommit
if (Test-Path $releaseRoot) { throw "Release output already exists: $releaseRoot" }
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

$archiveName = "monitor-comunitario-$resolvedCommit.tar"
$archivePath = Join-Path $releaseRoot $archiveName
Invoke-Git @("archive", "--format=tar", "--output=$archivePath", $resolvedCommit) | Out-Null

$files = @(Invoke-Git @("ls-tree", "-r", "--name-only", $resolvedCommit))
$manifest = [ordered]@{
    project = "monitor-comunitario"
    commit = $resolvedCommit
    archive = $archiveName
    archive_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant()
    tracked_file_count = $files.Count
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
}
$manifestPath = Join-Path $releaseRoot "release-manifest.json"
$manifestJson = $manifest | ConvertTo-Json
[System.IO.File]::WriteAllText($manifestPath, $manifestJson, [System.Text.UTF8Encoding]::new($false))
Write-Output "RELEASE_PREPARED commit=$resolvedCommit"
Write-Output "ARCHIVE=$archivePath"
Write-Output "MANIFEST=$(Join-Path $releaseRoot 'release-manifest.json')"
