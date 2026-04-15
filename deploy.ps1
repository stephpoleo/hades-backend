# Deploy script for Hades Backend to Cloud Run
# This script ensures all environment variables are preserved during deploy
# IMPORTANT: Runs tests before deploying - deploy is aborted if any test fails
#
# Options:
#   -SkipTests    Skip all tests (use when tests were already run locally)
#
# Examples:
#   .\deploy.ps1             # Run tests then deploy
#   .\deploy.ps1 -SkipTests  # Skip tests and deploy directly

param(
    [switch]$SkipTests = $false
)

$PROJECT_ID = "hades-backend-prod"
$REGION = "us-central1"
$SERVICE_NAME = "hades-backend"

# =============================================================================
# STEP 1: Run Unit Tests
# =============================================================================
if ($SkipTests) {
    Write-Host ""
    Write-Host "[WARNING] Skipping tests - NOT RECOMMENDED for production!" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host "  STEP 1: Running Unit Tests" -ForegroundColor Cyan
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host ""

    $venvPython = ".\venv\Scripts\python.exe"

    if (-Not (Test-Path $venvPython)) {
        Write-Host "ERROR: Virtual environment not found at $venvPython" -ForegroundColor Red
        Write-Host "Please create the virtual environment first: python -m venv venv" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Running tests with Django test runner..." -ForegroundColor Yellow
    & $venvPython manage.py test hades_app.tests --verbosity=1

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "=============================================" -ForegroundColor Red
        Write-Host "  TESTS FAILED - DEPLOY ABORTED" -ForegroundColor Red
        Write-Host "=============================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Fix the failing tests before deploying to production." -ForegroundColor Yellow
        Write-Host "Run 'python manage.py test hades_app.tests -v 2' for more details." -ForegroundColor Yellow
        exit 1
    }

    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host "  ALL TESTS PASSED" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host ""
}

# =============================================================================
# STEP 2: Deploy to Cloud Run
# =============================================================================
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  STEP 2: Deploying to Cloud Run" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Deploying $SERVICE_NAME to Cloud Run..." -ForegroundColor Cyan

# Deploy with all required environment variables
gcloud run deploy $SERVICE_NAME `
    --source . `
    --region $REGION `
    --allow-unauthenticated `
    --timeout=300 `
    --set-env-vars="DJANGO_ENV=prod,DEBUG=False,FORCE_HTTPS=true,HOST=hades-backend-694277248400.us-central1.run.app,DB_HOST=/cloudsql/hades-backend-prod:us-central1:hades-bd,DB_PORT=5432,DB_NAME=postgres,FRONT_ORIGIN=https://hades-frontend-694277248400.us-central1.run.app,API_ORIGIN=https://hades-backend-694277248400.us-central1.run.app,EDS_PROFILE=erelis,EDS_SOURCES=erelis,EDS_DB_TABLE=oasis_cat_eds,EDS_ERELIS_DB_ENGINE=hades_app.db_backends.postgres_compat,EDS_ERELIS_DB_NAME=postgres,EDS_ERELIS_DB_USER=erelis_admin,EDS_ERELIS_DB_HOST=erelis-prod.postgres.database.azure.com,EDS_ERELIS_DB_PORT=5432,EDS_ERELIS_DB_SSLMODE=require" `
    --set-secrets="SECRET_KEY=SECRET_KEY:latest,DB_PASSWORD=DB_PASSWORD:latest,DB_USER=DB_USER:latest,EDS_ERELIS_DB_PASSWORD=EDS_ERELIS_DB_PASSWORD:latest" `
    --add-cloudsql-instances=hades-backend-prod:us-central1:hades-bd

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host "  DEPLOY COMPLETED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service URL: https://hades-backend-694277248400.us-central1.run.app" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Red
    Write-Host "  DEPLOY FAILED" -ForegroundColor Red
    Write-Host "=============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Deploy failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
