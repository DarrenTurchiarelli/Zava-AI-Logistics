# =============================================================================
# Deploy DT Logistics to Azure App Service
# =============================================================================

param(
    [string]$ResourceGroup = "dt-logistics-rg",
    [string]$Location = "australiaeast",
    [string]$AppServicePlan = "dt-logistics-plan",
    [string]$WebAppName = "dt-logistics-web-$(Get-Random -Minimum 1000 -Maximum 9999)",
    [string]$Sku = "B2" #P1v2 is also good for production
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " DT Logistics - Azure App Service Deployment" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if logged in
Write-Host "[1/8] Checking Azure login status..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "✗ Not logged in to Azure. Running 'az login'..." -ForegroundColor Red
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Host "✓ Logged in as: $($account.user.name)" -ForegroundColor Green
Write-Host "✓ Subscription: $($account.name)" -ForegroundColor Green
Write-Host ""

# Create Resource Group
Write-Host "[2/8] Creating Resource Group: $ResourceGroup..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output none
Write-Host "✓ Resource Group created" -ForegroundColor Green
Write-Host ""

# Create App Service Plan
Write-Host "[3/8] Creating App Service Plan: $AppServicePlan..." -ForegroundColor Yellow
az appservice plan create `
    --name $AppServicePlan `
    --resource-group $ResourceGroup `
    --sku $Sku `
    --is-linux `
    --output none
Write-Host "✓ App Service Plan created (SKU: $Sku)" -ForegroundColor Green
Write-Host ""

# Create Web App
Write-Host "[4/8] Creating Web App: $WebAppName..." -ForegroundColor Yellow
az webapp create `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --plan $AppServicePlan `
    --runtime "PYTHON:3.11" `
    --output none
Write-Host "✓ Web App created" -ForegroundColor Green
Write-Host ""

# Enable system-assigned managed identity
Write-Host "[5/9] Enabling managed identity..." -ForegroundColor Yellow
az webapp identity assign `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --output none
Write-Host "✓ Managed identity enabled" -ForegroundColor Green
Write-Host ""

# Configure startup command
Write-Host "[6/9] Configuring startup command..." -ForegroundColor Yellow
az webapp config set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers=4 --threads=2 --worker-class=gthread app:app" `
    --output none
Write-Host "✓ Startup command configured" -ForegroundColor Green
Write-Host ""

# Set environment variables
Write-Host "[7/9] Setting environment variables..." -ForegroundColor Yellow

# Generate Flask secret key
$FlaskSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})

# Get existing .env values (if available)
$CosmosConnection = ""
$AzureAIConnection = ""
$AzureMapsKey = ""
$AzureVisionEndpoint = ""
$AzureVisionKey = ""

if (Test-Path ".env") {
    Write-Host "  Reading configuration from .env file..." -ForegroundColor Gray
    Get-Content .env | ForEach-Object {
        if ($_ -match '^COSMOS_CONNECTION_STRING\s*=\s*"?([^"]+)"?') {
            $CosmosConnection = $matches[1]
        }
        if ($_ -match '^AZURE_AI_PROJECT_CONNECTION_STRING\s*=\s*"?([^"]+)"?') {
            $AzureAIConnection = $matches[1]
        }
        if ($_ -match '^AZURE_MAPS_SUBSCRIPTION_KEY\s*=\s*"?([^"]+)"?') {
            $AzureMapsKey = $matches[1]
        }
        if ($_ -match '^AZURE_VISION_ENDPOINT\s*=\s*"?([^"]+)"?') {
            $AzureVisionEndpoint = $matches[1]
        }
        if ($_ -match '^AZURE_VISION_KEY\s*=\s*"?([^"]+)"?') {
            $AzureVisionKey = $matches[1]
        }
    }
}

# Prepare settings
$settings = @(
    "FLASK_SECRET_KEY=$FlaskSecret"
    "FLASK_ENV=production"
    "PORT=8000"
    "SCM_DO_BUILD_DURING_DEPLOYMENT=true"
)

if ($CosmosConnection) {
    $settings += "COSMOS_CONNECTION_STRING=$CosmosConnection"
    Write-Host "  ✓ Cosmos DB connection configured" -ForegroundColor Green
}
if ($AzureAIConnection) {
    $settings += "AZURE_AI_PROJECT_CONNECTION_STRING=$AzureAIConnection"
    Write-Host "  ✓ Azure AI Foundry connection configured" -ForegroundColor Green
}
if ($AzureMapsKey) {
    $settings += "AZURE_MAPS_SUBSCRIPTION_KEY=$AzureMapsKey"
    Write-Host "  ✓ Azure Maps key configured" -ForegroundColor Green
}
if ($AzureVisionEndpoint) {
    $settings += "AZURE_VISION_ENDPOINT=$AzureVisionEndpoint"
    Write-Host "  ✓ Azure Vision endpoint configured" -ForegroundColor Green
}
if ($AzureVisionKey) {
    $settings += "AZURE_VISION_KEY=$AzureVisionKey"
    Write-Host "  ✓ Azure Vision key configured" -ForegroundColor Green
}

az webapp config appsettings set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --settings $settings `
    --output none

Write-Host "✓ Environment variables configured" -ForegroundColor Green
Write-Host ""

# Deploy application
Write-Host "[8/9] Deploying application code..." -ForegroundColor Yellow
Write-Host "  This may take 3-5 minutes..." -ForegroundColor Gray

# Create a deployment ZIP (excluding unnecessary files)
$tempZip = "$env:TEMP\dt-logistics-deploy.zip"
if (Test-Path $tempZip) { Remove-Item $tempZip -Force }

# Files/folders to exclude
$excludeList = @(
    "__pycache__",
    "*.pyc",
    ".git",
    ".env",
    ".venv",
    "venv",
    "*.md",
    "Test Scripts",
    "Scripts",
    "Guides"
)

# Create deployment package
Compress-Archive -Path * -DestinationPath $tempZip -Force

# Deploy ZIP
az webapp deployment source config-zip `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --src $tempZip `
    --timeout 600

Remove-Item $tempZip -Force

Write-Host "✓ Application deployed" -ForegroundColor Green
Write-Host ""

# Configure additional settings
Write-Host "[9/9] Configuring additional settings..." -ForegroundColor Yellow

# Enable Always On (requires Basic or higher SKU)
if ($Sku -ne "F1" -and $Sku -ne "D1") {
    az webapp config set `
        --name $WebAppName `
        --resource-group $ResourceGroup `
        --always-on true `
        --output none
    Write-Host "  ✓ Always On enabled" -ForegroundColor Green
}

# Enable logging
az webapp log config `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --application-logging filesystem `
    --detailed-error-messages true `
    --web-server-logging filesystem `
    --output none
Write-Host "  ✓ Logging configured" -ForegroundColor Green

# Enable HTTPS only
az webapp update `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --https-only true `
    --output none
Write-Host "  ✓ HTTPS-only enabled" -ForegroundColor Green
Write-Host ""

# Get URL
$url = "https://$WebAppName.azurewebsites.net"

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application URL: $url" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Visit: $url" -ForegroundColor White
Write-Host "  2. Login with default credentials:" -ForegroundColor White
Write-Host "     Username: admin" -ForegroundColor White
Write-Host "     Password: admin123" -ForegroundColor White
Write-Host ""
Write-Host "  3. View logs: az webapp log tail --name $WebAppName --resource-group $ResourceGroup" -ForegroundColor White
Write-Host "  4. Manage in portal: https://portal.azure.com" -ForegroundColor White
Write-Host ""
Write-Host "To update the application:" -ForegroundColor Yellow
Write-Host "  Run this script again to redeploy" -ForegroundColor White
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan

# Copy URL to clipboard
$url | Set-Clipboard
Write-Host "✓ URL copied to clipboard!" -ForegroundColor Green
