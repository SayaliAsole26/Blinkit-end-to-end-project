# Push Blinkit project to GitHub (run after Git is installed)
# Usage: .\scripts\push_to_github.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$remote = "https://github.com/SayaliAsole26/Blinkit-end-to-end-project.git"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git not found. Install from https://git-scm.com/download/win then re-run this script."
}

# Safety: never commit secrets
if (Test-Path .env) {
    git check-ignore -q .env 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Error ".env is not gitignored — aborting to protect secrets."
    }
}

if (-not (Test-Path .git)) {
    git init
    git branch -M main
}

git remote remove origin 2>$null
git remote add origin $remote

git add .
git status

$status = git status --porcelain
if (-not $status) {
    Write-Host "Nothing to commit."
} else {
    git commit -m "$( @'
Initial commit: Blinkit review analyzer pipeline (Phases 0-3).

Includes ingestion, clean/embed, dual-track clustering, Groq labeling,
config, tests, and documentation. Secrets and local data excluded via .gitignore.
'@ )"
}

Write-Host "Pushing to $remote ..."
git push -u origin main

Write-Host "Done."
