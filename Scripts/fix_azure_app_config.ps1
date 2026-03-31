# Quick Fix: Update Azure App Service configuration with correct endpoints
# This fixes environment variables in Azure to match the current deployment

Write-Host "`n🔧 FIXING AZURE APP SERVICE CONFIGURATION`n" -ForegroundColor Cyan

# Find the deployed web app
Write-Host "1. Finding deployed web app..." -ForegroundColor Yellow
$webApp = az webapp list --query "[?contains(name, 'zava-dev-web')].{Name:name, ResourceGroup:resourceGroup}" -o json | ConvertFrom-Json | Select-Object -First 1

if (-not $webApp) {
    Write-Host "   ✗ No Zava web app found in Azure" -ForegroundColor Red
    exit 1
}

$webAppName = $webApp.Name
$frontendRg = $webApp.ResourceGroup
$suffix = $webAppName -replace 'zava-dev-web-', ''

Write-Host "   ✓ Found: $webAppName (suffix: $suffix)`n" -ForegroundColor Green

# Get resource names
$cosmosName = "zava-dev-cosmos-$suffix"
$openAIName = "zava-dev-openai-$suffix"
$backendRg = "RG-Zava-Backend-dev"
$middlewareRg = "RG-Zava-Middleware-dev"

# Get endpoints
Write-Host "2. Retrieving Azure resource endpoints..." -ForegroundColor Yellow

$cosmosEndpoint = az cosmosdb show --name $cosmosName --resource-group $backendRg --query "documentEndpoint" -o tsv
$openAIEndpoint = az cognitiveservices account show --name $openAIName --resource-group $middlewareRg --query "properties.endpoint" -o tsv

Write-Host "   ✓ Cosmos DB: $cosmosEndpoint" -ForegroundColor Green
Write-Host "   ✓ Azure OpenAI: $openAIEndpoint`n" -ForegroundColor Green

# Get current agent IDs from app settings
Write-Host "3. Retrieving current agent IDs..." -ForegroundColor Yellow
$currentSettings = az webapp config appsettings list --name $webAppName --resource-group $frontendRg -o json | ConvertFrom-Json

$settingsDict = @{}
foreach ($setting in $currentSettings) {
    $settingsDict[$setting.name] = $setting.value
}

$agentIds = @(
    'CUSTOMER_SERVICE_AGENT_ID',
    'FRAUD_RISK_AGENT_ID',
    'IDENTITY_AGENT_ID',
    'DISPATCHER_AGENT_ID',
    'PARCEL_INTAKE_AGENT_ID',
    'SORTING_FACILITY_AGENT_ID',
    'DELIVERY_COORDINATION_AGENT_ID',
    'OPTIMIZATION_AGENT_ID'
)

$hasAllAgents = $true
foreach ($agentId in $agentIds) {
    if ($settingsDict[$agentId] -and $settingsDict[$agentId] -match '^asst_') {
        Write-Host "   ✓ $agentId found" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $agentId missing or invalid" -ForegroundColor Red
        $hasAllAgents = $false
    }
}

# Build settings array with correct endpoints
Write-Host "`n4. Updating Azure App Service configuration..." -ForegroundColor Yellow

$settings = @(
    "COSMOS_DB_ENDPOINT=$cosmosEndpoint",
    "COSMOS_DB_DATABASE_NAME=logisticstracking",
    "AZURE_OPENAI_ENDPOINT=$openAIEndpoint",
    "AZURE_AI_PROJECT_ENDPOINT=https://australiaeast.api.azureml.ms/discovery",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o",
    "USE_MANAGED_IDENTITY=true",
    "WEBSITES_PORT=8000",
    "PORT=8000"
)

# Remove any old connection strings (should use managed identity)
Write-Host "   🧹 Removing old connection strings..." -ForegroundColor Gray
az webapp config appsettings delete `
    --name $webAppName `
    --resource-group $frontendRg `
    --setting-names COSMOS_CONNECTION_STRING COSMOS_DB_KEY `
    --output none 2>$null

# Apply new settings
az webapp config appsettings set `
    --name $webAppName `
    --resource-group $frontendRg `
    --settings $settings `
    --output none

Write-Host "   ✓ Environment variables updated" -ForegroundColor Green

# Set startup command
Write-Host "   🚀 Setting startup command..." -ForegroundColor Gray
az webapp config set `
    --name $webAppName `
    --resource-group $frontendRg `
    --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app" `
    --output none

Write-Host "   ✓ Startup command configured" -ForegroundColor Green

# Restart app
Write-Host "`n5. Restarting application..." -ForegroundColor Yellow
az webapp restart --name $webAppName --resource-group $frontendRg --output none

Write-Host "   ✓ App restarted`n" -ForegroundColor Green

Write-Host "⏱  Waiting 45 seconds for app to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 45

# Test endpoint
Write-Host "`n6. Testing application..." -ForegroundColor Yellow
$url = "https://$webAppName.azurewebsites.net"

try {
    $response = Invoke-WebRequest -Uri $url -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ App is responding! Status: 200 OK`n" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  App responded with: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   Check logs: az webapp log tail --name $webAppName --resource-group $frontendRg`n" -ForegroundColor Gray
}

Write-Host "✅ CONFIGURATION FIXED!`n" -ForegroundColor Green
Write-Host "Your app URL: $url" -ForegroundColor Cyan
Write-Host "Login: admin / admin123`n" -ForegroundColor White

if (-not $hasAllAgents) {
    Write-Host "⚠️  WARNING: Some agent IDs are missing" -ForegroundColor Yellow
    Write-Host "   Agents may not work until IDs are configured" -ForegroundColor Gray
    Write-Host "   Run: python Scripts/create_foundry_agents_openai.py`n" -ForegroundColor White
}
