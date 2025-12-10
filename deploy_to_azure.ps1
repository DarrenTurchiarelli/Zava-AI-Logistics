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
Write-Host "[1/11] Checking Azure login status..." -ForegroundColor Yellow
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
Write-Host "[2/11] Creating Resource Group: $ResourceGroup..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output none
Write-Host "✓ Resource Group created" -ForegroundColor Green
Write-Host ""

# Create App Service Plan
Write-Host "[3/11] Creating App Service Plan: $AppServicePlan..." -ForegroundColor Yellow
az appservice plan create `
    --name $AppServicePlan `
    --resource-group $ResourceGroup `
    --sku $Sku `
    --is-linux `
    --output none
Write-Host "✓ App Service Plan created (SKU: $Sku)" -ForegroundColor Green
Write-Host ""

# Create Web App
Write-Host "[4/11] Creating Web App: $WebAppName..." -ForegroundColor Yellow
az webapp create `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --plan $AppServicePlan `
    --runtime "PYTHON:3.11" `
    --output none
Write-Host "✓ Web App created" -ForegroundColor Green
Write-Host ""

# Enable system-assigned managed identity
Write-Host "[5/11] Enabling managed identity..." -ForegroundColor Yellow
az webapp identity assign `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --output none
Write-Host "✓ Managed identity enabled" -ForegroundColor Green
Write-Host ""

# Configure startup command
Write-Host "[6/11] Configuring startup command..." -ForegroundColor Yellow
az webapp config set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers=4 --threads=2 --worker-class=gthread app:app" `
    --output none
Write-Host "✓ Startup command configured" -ForegroundColor Green
Write-Host ""

# Set environment variables
Write-Host "[7/11] Setting environment variables..." -ForegroundColor Yellow

# Generate Flask secret key
$FlaskSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})

# Get existing .env values (if available)
$CosmosConnection = ""
$CosmosEndpoint = ""
$CosmosKey = ""
$CosmosDatabaseName = ""
$AzureAIConnection = ""
$AzureAIEndpoint = ""
$AzureAIModel = ""
$AzureMapsKey = ""
$AzureVisionEndpoint = ""
$AzureVisionKey = ""
$DepotNSW = ""
$DepotVIC = ""
$DepotQLD = ""
$DepotSA = ""
$DepotWA = ""
$DepotTAS = ""
$DepotACT = ""
$DepotNT = ""

if (Test-Path ".env") {
    Write-Host "  Reading configuration from .env file..." -ForegroundColor Gray
    Get-Content .env | ForEach-Object {
        if ($_ -match '^COSMOS_CONNECTION_STRING\s*=\s*"?([^"]+)"?') {
            $CosmosConnection = $matches[1]
        }
        if ($_ -match '^COSMOS_DB_ENDPOINT\s*=\s*"?([^"]+)"?') {
            $CosmosEndpoint = $matches[1]
        }
        if ($_ -match '^COSMOS_DB_KEY\s*=\s*"?([^"]+)"?') {
            $CosmosKey = $matches[1]
        }
        if ($_ -match '^COSMOS_DB_DATABASE_NAME\s*=\s*"?([^"]+)"?') {
            $CosmosDatabaseName = $matches[1]
        }
        if ($_ -match '^AZURE_AI_PROJECT_CONNECTION_STRING\s*=\s*"?([^"]+)"?') {
            $AzureAIConnection = $matches[1]
        }
        if ($_ -match '^AZURE_AI_PROJECT_ENDPOINT\s*=\s*"?([^"]+)"?') {
            $AzureAIEndpoint = $matches[1]
        }
        if ($_ -match '^AZURE_AI_MODEL_DEPLOYMENT_NAME\s*=\s*"?([^"]+)"?') {
            $AzureAIModel = $matches[1]
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
        if ($_ -match '^DEPOT_NSW\s*=\s*"?([^"]+)"?') {
            $DepotNSW = $matches[1]
        }
        if ($_ -match '^DEPOT_VIC\s*=\s*"?([^"]+)"?') {
            $DepotVIC = $matches[1]
        }
        if ($_ -match '^DEPOT_QLD\s*=\s*"?([^"]+)"?') {
            $DepotQLD = $matches[1]
        }
        if ($_ -match '^DEPOT_SA\s*=\s*"?([^"]+)"?') {
            $DepotSA = $matches[1]
        }
        if ($_ -match '^DEPOT_WA\s*=\s*"?([^"]+)"?') {
            $DepotWA = $matches[1]
        }
        if ($_ -match '^DEPOT_TAS\s*=\s*"?([^"]+)"?') {
            $DepotTAS = $matches[1]
        }
        if ($_ -match '^DEPOT_ACT\s*=\s*"?([^"]+)"?') {
            $DepotACT = $matches[1]
        }
        if ($_ -match '^DEPOT_NT\s*=\s*"?([^"]+)"?') {
            $DepotNT = $matches[1]
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
    Write-Host "  ✓ Cosmos DB connection string configured" -ForegroundColor Green
}
if ($CosmosEndpoint) {
    $settings += "COSMOS_DB_ENDPOINT=$CosmosEndpoint"
    Write-Host "  ✓ Cosmos DB endpoint configured" -ForegroundColor Green
}
if ($CosmosKey) {
    $settings += "COSMOS_DB_KEY=$CosmosKey"
    Write-Host "  ✓ Cosmos DB key configured" -ForegroundColor Green
}
if ($CosmosDatabaseName) {
    $settings += "COSMOS_DB_DATABASE_NAME=$CosmosDatabaseName"
    Write-Host "  ✓ Cosmos DB database name configured" -ForegroundColor Green
}
if ($AzureAIConnection) {
    $settings += "AZURE_AI_PROJECT_CONNECTION_STRING=$AzureAIConnection"
    Write-Host "  ✓ Azure AI Foundry connection string configured" -ForegroundColor Green
}
if ($AzureAIEndpoint) {
    $settings += "AZURE_AI_PROJECT_ENDPOINT=$AzureAIEndpoint"
    Write-Host "  ✓ Azure AI Foundry endpoint configured" -ForegroundColor Green
}
if ($AzureAIModel) {
    $settings += "AZURE_AI_MODEL_DEPLOYMENT_NAME=$AzureAIModel"
    Write-Host "  ✓ Azure AI model deployment configured" -ForegroundColor Green
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
if ($DepotNSW) {
    $settings += "DEPOT_NSW=$DepotNSW"
}
if ($DepotVIC) {
    $settings += "DEPOT_VIC=$DepotVIC"
}
if ($DepotQLD) {
    $settings += "DEPOT_QLD=$DepotQLD"
}
if ($DepotSA) {
    $settings += "DEPOT_SA=$DepotSA"
}
if ($DepotWA) {
    $settings += "DEPOT_WA=$DepotWA"
}
if ($DepotTAS) {
    $settings += "DEPOT_TAS=$DepotTAS"
}
if ($DepotACT) {
    $settings += "DEPOT_ACT=$DepotACT"
}
if ($DepotNT) {
    $settings += "DEPOT_NT=$DepotNT"
}
if ($DepotNSW -or $DepotVIC -or $DepotQLD -or $DepotSA -or $DepotWA -or $DepotTAS -or $DepotACT -or $DepotNT) {
    Write-Host "  ✓ Depot addresses configured" -ForegroundColor Green
}

az webapp config appsettings set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --settings $settings `
    --output none

Write-Host "✓ Environment variables configured" -ForegroundColor Green
Write-Host ""

# Grant Cosmos DB RBAC permissions to managed identity
Write-Host "[8/11] Configuring Cosmos DB permissions..." -ForegroundColor Yellow
if ($CosmosEndpoint) {
    # Extract Cosmos DB account name from endpoint
    if ($CosmosEndpoint -match "https://([^.]+)\.documents\.azure\.com") {
        $CosmosAccountName = $matches[1]
        
        # Get the managed identity principal ID
        $principalId = az webapp identity show --name $WebAppName --resource-group $ResourceGroup --query principalId -o tsv
        
        if ($principalId) {
            Write-Host "  Managed Identity Principal ID: $principalId" -ForegroundColor Gray
            
            # Try to find the Cosmos DB account
            $cosmosAccount = az cosmosdb list --query "[?name=='$CosmosAccountName'].{name:name, resourceGroup:resourceGroup}" -o json | ConvertFrom-Json
            
            if ($cosmosAccount -and $cosmosAccount.Count -gt 0) {
                $cosmosRG = $cosmosAccount[0].resourceGroup
                Write-Host "  Found Cosmos DB '$CosmosAccountName' in resource group '$cosmosRG'" -ForegroundColor Gray
                
                # Grant Cosmos DB Built-in Data Contributor role
                try {
                    az cosmosdb sql role assignment create `
                        --account-name $CosmosAccountName `
                        --resource-group $cosmosRG `
                        --role-definition-name "Cosmos DB Built-in Data Contributor" `
                        --principal-id $principalId `
                        --scope "/" `
                        --output none 2>$null
                    
                    Write-Host "  ✓ Cosmos DB RBAC permissions granted" -ForegroundColor Green
                } catch {
                    # Role assignment might already exist
                    Write-Host "  ⚠ Cosmos DB permissions may already be configured" -ForegroundColor Yellow
                }
            } else {
                Write-Host "  ⚠ Could not find Cosmos DB account '$CosmosAccountName'" -ForegroundColor Yellow
                Write-Host "  You may need to grant RBAC permissions manually:" -ForegroundColor Yellow
                Write-Host "    az cosmosdb sql role assignment create --account-name $CosmosAccountName --role-definition-name 'Cosmos DB Built-in Data Contributor' --principal-id $principalId --scope '/'" -ForegroundColor Gray
            }
        }
    }
} else {
    Write-Host "  ⊘ Cosmos DB endpoint not configured, skipping RBAC setup" -ForegroundColor Gray
}
Write-Host ""

# Deploy application
Write-Host "[9/11] Deploying application code..." -ForegroundColor Yellow
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
Write-Host "[10/11] Configuring additional settings..." -ForegroundColor Yellow

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

# Initialize users in Cosmos DB
Write-Host "[11/11] Initializing default users..." -ForegroundColor Yellow
if (Test-Path "init_azure_users.py") {
    try {
        python init_azure_users.py
        Write-Host "  ✓ Default users initialized" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ User initialization failed (users may already exist)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ init_azure_users.py not found, skipping user initialization" -ForegroundColor Yellow
    Write-Host "  You may need to run setup_users.py manually after deployment" -ForegroundColor Gray
}
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
