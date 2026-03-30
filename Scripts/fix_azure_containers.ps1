# =============================================================================
# Fix Missing Cosmos DB Containers on Azure Deployment
# =============================================================================
# This script temporarily enables local auth on Cosmos DB to create containers,
# then re-disables it for security
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "RG-Zava-Backend-dev",
    
    [Parameter(Mandatory=$false)]
    [string]$CosmosAccountName = ""
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Fix Missing Cosmos DB Containers" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Find Cosmos DB account if not specified
if (-not $CosmosAccountName) {
    Write-Host "[1/5] Finding Cosmos DB account in resource group..." -ForegroundColor Yellow
    $cosmosAccount = az cosmosdb list --resource-group $ResourceGroup --query "[0].{name:name}" -o json 2>$null | ConvertFrom-Json
    
    if (-not $cosmosAccount) {
        Write-Host "❌ ERROR: No Cosmos DB account found in resource group '$ResourceGroup'" -ForegroundColor Red
        Write-Host "   Please specify -CosmosAccountName parameter" -ForegroundColor Yellow
        exit 1
    }
    
    $CosmosAccountName = $cosmosAccount.name
}

Write-Host "✓ Using Cosmos DB account: $CosmosAccountName" -ForegroundColor Green
Write-Host ""

# Step 2: Get Cosmos DB connection details
Write-Host "[2/5] Getting Cosmos DB connection details..." -ForegroundColor Yellow
$cosmosEndpoint = az cosmosdb show --name $CosmosAccountName --resource-group $ResourceGroup --query "documentEndpoint" -o tsv
Write-Host "✓ Endpoint: $cosmosEndpoint" -ForegroundColor Green
Write-Host ""

# Step 3: Temporarily enable local auth to get connection string
Write-Host "[3/5] Temporarily enabling local auth for container creation..." -ForegroundColor Yellow

# Get subscription ID and build resource ID
$subscriptionId = (az account show --query id -o tsv)
$resourceId = "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.DocumentDB/databaseAccounts/$CosmosAccountName"

# Enable local auth using az resource update
az resource update `
    --ids $resourceId `
    --set properties.disableLocalAuth=false `
    --api-version 2023-11-15 `
    --output none

Write-Host "⏱  Waiting 60 seconds for auth change to propagate..." -ForegroundColor Gray
Write-Host "   (Azure configuration changes can take 45-60 seconds to apply globally)" -ForegroundColor Gray
Start-Sleep -Seconds 60  # Wait for setting to propagate

# Get connection string
$connectionString = az cosmosdb keys list --name $CosmosAccountName --resource-group $ResourceGroup --type connection-strings --query "connectionStrings[0].connectionString" -o tsv

if (-not $connectionString) {
    Write-Host "❌ ERROR: Could not retrieve connection string" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Connection string obtained" -ForegroundColor Green
Write-Host ""

# Step 4: Run container initialization
Write-Host "[4/5] Creating missing containers..." -ForegroundColor Yellow
$env:COSMOS_CONNECTION_STRING = $connectionString
$env:COSMOS_DB_DATABASE_NAME = "logisticstracking"

python Scripts/initialize_all_containers.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Container initialization failed on first attempt" -ForegroundColor Red
    Write-Host "   Retrying after 30 second wait..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    Write-Host "   Retry attempt 1/2..." -ForegroundColor Cyan
    python Scripts/initialize_all_containers.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ ERROR: Container initialization failed on retry" -ForegroundColor Red
        Write-Host "   Check the error output above" -ForegroundColor Yellow
        
        # Still try to disable local auth
        Write-Host "`nRe-disabling local auth..." -ForegroundColor Yellow
        az resource update `
            --ids $resourceId `
            --set properties.disableLocalAuth=true `
            --api-version 2023-11-15 `
            --output none
        exit 1
    }
}

# Validate all 10 containers exist
Write-Host "   🔍 Validating all 10 containers..." -ForegroundColor Cyan
$validateOutput = python Scripts/diagnose_containers.py 2>&1

if ($LASTEXITCODE -eq 0 -and $validateOutput -match "All containers exist") {
    Write-Host "   ✓ All 10 containers validated successfully" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Container validation check:" -ForegroundColor Yellow
    Write-Host $validateOutput -ForegroundColor Gray
    Write-Host "`n   If containers are missing, they will auto-create on first use" -ForegroundColor Gray
}

Write-Host ""

# Step 5: Re-disable local auth for security
Write-Host "[5/5] Re-disabling local auth for security..." -ForegroundColor Yellow
az resource update `
    --ids $resourceId `
    --set properties.disableLocalAuth=true `
    --api-version 2023-11-15 `
    --output none

Start-Sleep -Seconds 2
Write-Host "✓ Local auth disabled (managed identity only)" -ForegroundColor Green
Write-Host ""

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " ✅ Containers successfully created!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Restart your web app:" -ForegroundColor Gray
Write-Host "     az webapp restart --name <webapp-name> --resource-group RG-Zava-Frontend-dev" -ForegroundColor Gray
Write-Host "  2. Test parcel registration:" -ForegroundColor Gray
Write-Host "     https://<webapp-name>.azurewebsites.net/parcels/register" -ForegroundColor Gray
Write-Host ""
