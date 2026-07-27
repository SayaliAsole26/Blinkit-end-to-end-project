# Deploy blinkit-api to Railway
# Prerequisites: RAILWAY_TOKEN env var OR run `railway login` once interactively
# Usage:
#   .\scripts\deploy_railway.ps1
#   $env:RAILWAY_TOKEN="..." ; .\scripts\deploy_railway.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$railway = Join-Path $PWD ".tools\railway.exe"
if (-not (Test-Path $railway)) {
    Write-Error "Railway CLI not found at $railway. Run from repo root after downloading CLI to .tools/"
}

# Required seed data (baked into Docker image via Dockerfile)
$required = @(
    "deploy\seed\insights\insights_run_phase4_final.json",
    "deploy\seed\processed\validation_run_phase4_final.json",
    "deploy\seed\processed\synthesize_validate_summary_run_phase4_final.json"
)
foreach ($f in $required) {
    if (-not (Test-Path $f)) {
        Write-Error "Missing seed file: $f"
    }
}

Write-Host "=== Railway deploy: blinkit-api ===" -ForegroundColor Cyan
& $railway --version

if (-not $env:RAILWAY_TOKEN) {
    Write-Host "Tip: set RAILWAY_TOKEN for non-interactive deploy (Railway dashboard -> Account -> Tokens)"
    $whoami = & $railway whoami 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Not logged in. Run: .\.tools\railway.exe login" -ForegroundColor Yellow
        exit 1
    }
}

# Link or init project if not already linked
if (-not (Test-Path ".railway")) {
    if ($env:CI -or $env:RAILWAY_TOKEN) {
        Write-Host "Initializing Railway project..."
        & $railway init --name blinkit-api
    } else {
        Write-Host "Linking Railway project (select existing or create blinkit-api)..."
        & $railway link
    }
}

Write-Host "Setting environment variables..."
& $railway variables set `
    BLINKIT_DATA_DIR=/app/data `
    INSIGHTS_RUN_ID=run_phase4_final `
    CORS_ORIGINS="https://blinkit-end-to-end-project.vercel.app,http://localhost:3000" `
    LOG_LEVEL=INFO `
    ENABLE_OPENAPI=false

Write-Host "Deploying (Docker target: api)..."
& $railway up --detach

Write-Host ""
Write-Host "After deploy completes, verify:" -ForegroundColor Green
Write-Host "  railway domain"
Write-Host "  curl https://<your-domain>/health"
Write-Host "  curl https://<your-domain>/api/overview"
Write-Host ""
Write-Host "Update frontend/vercel.json /api proxy if domain changed."
