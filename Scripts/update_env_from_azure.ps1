# Update .env file from current Azure deployment
# This script syncs your local .env file with the currently deployed Azure resources

Write-Host "`n📝 UPDATING .ENV FROM AZURE DEPLOYMENT`n" -ForegroundColor Cyan

# Find the deployed web app
Write-Host "1. Finding deployed web app..." -ForegroundColor Yellow
$webApp = az webapp list --query "[?contains(name, 'zava-dev-web')].{Name:name, ResourceGroup:resourceGroup}" -o json | ConvertFrom-Json | Select-Object -First 1

if (-not $webApp) {
    Write-Host "   ✗ No Zava web app found in Azure" -ForegroundColor Red
    Write-Host "   Deploy first with: .\deploy_to_azure.ps1`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "   ✓ Found: $($webApp.Name)" -ForegroundColor Green
$webAppName = $webApp.Name
$frontendRg = $webApp.ResourceGroup

# Extract suffix from web app name (e.g., "zava-dev-web-aixqdm" -> "aixqdm")
$suffix = $webAppName -replace 'zava-dev-web-', ''
Write-Host "   Deployment suffix: $suffix`n" -ForegroundColor Gray

# Get environment variables from App Service
Write-Host "2. Retrieving configuration from Azure..." -ForegroundColor Yellow
$settings = az webapp config appsettings list --name $webAppName --resource-group $frontendRg -o json | ConvertFrom-Json

# Create lookup dictionary
$settingsDict = @{}
foreach ($setting in $settings) {
    $settingsDict[$setting.name] = $setting.value
}

# Get Cosmos DB connection string (for local dev)
Write-Host "3. Retrieving Cosmos DB connection string..." -ForegroundColor Yellow
$cosmosAccountName = "zava-dev-cosmos-$suffix"
$backendRg = "RG-Zava-Backend-dev"
$cosmosConnectionString = ""

try {
    $cosmosConnectionString = az cosmosdb keys list `
        --name $cosmosAccountName `
        --resource-group $backendRg `
        --type connection-strings `
        --query "connectionStrings[0].connectionString" `
        -o tsv 2>$null
    
    if ($cosmosConnectionString) {
        Write-Host "   ✓ Connection string retrieved" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Connection string not available (local auth disabled)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠ Could not retrieve connection string" -ForegroundColor Yellow
}

# Update .env file
Write-Host "`n4. Updating .env file..." -ForegroundColor Yellow
$envFilePath = Join-Path $PSScriptRoot ".." ".env"

if (-not (Test-Path $envFilePath)) {
    Write-Host "   ✗ .env file not found at: $envFilePath" -ForegroundColor Red
    exit 1
}

# Read current .env
$envContent = Get-Content $envFilePath -Raw

# Update values
$updates = @{
    'COSMOS_DB_ENDPOINT' = $settingsDict['COSMOS_DB_ENDPOINT']
    'COSMOS_DB_DATABASE_NAME' = $settingsDict['COSMOS_DB_DATABASE_NAME']
    'AZURE_AI_PROJECT_ENDPOINT' = $settingsDict['AZURE_AI_PROJECT_ENDPOINT']
    'AZURE_OPENAI_ENDPOINT' = $settingsDict['AZURE_OPENAI_ENDPOINT']
    'AZURE_AI_MODEL_DEPLOYMENT_NAME' = $settingsDict['AZURE_AI_MODEL_DEPLOYMENT_NAME']
    'PARCEL_INTAKE_AGENT_ID' = $settingsDict['PARCEL_INTAKE_AGENT_ID']
    'SORTING_FACILITY_AGENT_ID' = $settingsDict['SORTING_FACILITY_AGENT_ID']
    'DELIVERY_COORDINATION_AGENT_ID' = $settingsDict['DELIVERY_COORDINATION_AGENT_ID']
    'DISPATCHER_AGENT_ID' = $settingsDict['DISPATCHER_AGENT_ID']
    'OPTIMIZATION_AGENT_ID' = $settingsDict['OPTIMIZATION_AGENT_ID']
    'CUSTOMER_SERVICE_AGENT_ID' = $settingsDict['CUSTOMER_SERVICE_AGENT_ID']
    'FRAUD_RISK_AGENT_ID' = $settingsDict['FRAUD_RISK_AGENT_ID']
    'IDENTITY_AGENT_ID' = $settingsDict['IDENTITY_AGENT_ID']
}

$updatedCount = 0
foreach ($key in $updates.Keys) {
    $value = $updates[$key]
    if ($value) {
        $envContent = $envContent -replace "$key=.*", "$key=$value"
        $updatedCount++
        Write-Host "   ✓ Updated $key" -ForegroundColor Green
    }
}

# Update connection string if available
if ($cosmosConnectionString) {
    $envContent = $envContent -replace 'COSMOS_CONNECTION_STRING=.*', "COSMOS_CONNECTION_STRING=$cosmosConnectionString"
    $updatedCount++
    Write-Host "   ✓ Updated COSMOS_CONNECTION_STRING" -ForegroundColor Green
}

# Add timestamp
$timestamp = Get-Date -Format "MMMM dd, yyyy HH:mm"
$envContent = $envContent -replace '# Azure AI Agents \(Updated:.*\)', "# Azure AI Agents (Updated: $timestamp - Synced from Azure)"

# Write updated content
Set-Content -Path $envFilePath -Value $envContent -NoNewline

Write-Host "`n✅ SUCCESS: .env file updated!" -ForegroundColor Green
Write-Host "   $updatedCount settings synchronized" -ForegroundColor Gray
Write-Host "   Deployment suffix: $suffix" -ForegroundColor Gray
Write-Host "   Local development now configured for Azure deployment`n" -ForegroundColor Gray
