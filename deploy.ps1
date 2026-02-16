# Deploy script for Hades Backend to Cloud Run
# This script ensures all environment variables are preserved during deploy

$PROJECT_ID = "hades-backend-prod"
$REGION = "us-central1"
$SERVICE_NAME = "hades-backend"

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
    Write-Host "Deploy completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Deploy failed with exit code $LASTEXITCODE" -ForegroundColor Red
}
