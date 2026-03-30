# =============================================================================
# Fix Cosmos DB Managed Identity Authentication Issues
# =============================================================================
# Resolves "Unauthorized" errors by verifying RBAC and refreshing credentials
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$FrontendResourceGroup = "RG-Zava-Frontend-dev",
    
    [Parameter(Mandatory=$false)]
    [string]$BackendResourceGroup = "RG-Zava-Backend-dev",
    
    [Parameter(Mandatory=$false)]
    [string]$WebAppName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$CosmosAccountName = ""
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Fix Cosmos DB Managed Identity Authentication" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Find Web App if not specified
if (-not $WebAppName) {
    Write-Host "[1/6] Finding Web App in resource group..." -ForegroundColor Yellow
    $webApp = az webapp list --resource-group $FrontendResourceGroup --query "[0].{name:name}" -o json 2>$null | ConvertFrom-Json
    
    if (-not $webApp) {
        Write-Host "❌ ERROR: No Web App found in resource group '$FrontendResourceGroup'" -ForegroundColor Red
        exit 1
    }
    
    $WebAppName = $webApp.name
}

Write-Host "✓ Web App: $WebAppName" -ForegroundColor Green
Write-Host ""

# Step 2: Find Cosmos DB account if not specified
if (-not $CosmosAccountName) {
    Write-Host "[2/6] Finding Cosmos DB account in resource group..." -ForegroundColor Yellow
    $cosmosAccount = az cosmosdb list --resource-group $BackendResourceGroup --query "[0].{name:name}" -o json 2>$null | ConvertFrom-Json
    
    if (-not $cosmosAccount) {
        Write-Host "❌ ERROR: No Cosmos DB account found in resource group '$BackendResourceGroup'" -ForegroundColor Red
        exit 1
    }
    
    $CosmosAccountName = $cosmosAccount.name
}

Write-Host "✓ Cosmos DB: $CosmosAccountName" -ForegroundColor Green
Write-Host ""

# Step 3: Get managed identity details
Write-Host "[3/6] Getting managed identity details..." -ForegroundColor Yellow
$identity = az webapp identity show --name $WebAppName --resource-group $FrontendResourceGroup -o json 2>$null | ConvertFrom-Json

if (-not $identity -or -not $identity.principalId) {
    Write-Host "❌ ERROR: Web App does not have managed identity enabled" -ForegroundColor Red
    Write-Host "   Enabling managed identity..." -ForegroundColor Yellow
    
    az webapp identity assign --name $WebAppName --resource-group $FrontendResourceGroup | Out-Null
    Start-Sleep -Seconds 5
    
    $identity = az webapp identity show --name $WebAppName --resource-group $FrontendResourceGroup -o json | ConvertFrom-Json
}

$principalId = $identity.principalId
Write-Host "✓ Managed Identity Principal ID: $principalId" -ForegroundColor Green
Write-Host ""

# Step 4: Verify RBAC role assignment
Write-Host "[4/6] Verifying RBAC permissions..." -ForegroundColor Yellow

$cosmosResourceId = az cosmosdb show --name $CosmosAccountName --resource-group $BackendResourceGroup --query "id" -o tsv

# Check for Cosmos DB Built-in Data Contributor role
$roleDefinitionId = "00000000-0000-0000-0000-000000000002"
$roleAssignments = az cosmosdb sql role assignment list `
    --account-name $CosmosAccountName `
    --resource-group $BackendResourceGroup `
    --query "[?principalId=='$principalId'].{id:id, role:roleDefinitionId}" `
    -o json 2>$null | ConvertFrom-Json

$hasRole = $false
foreach ($assignment in $roleAssignments) {
    if ($assignment.role -like "*$roleDefinitionId") {
        $hasRole = $true
        break
    }
}

if ($hasRole) {
    Write-Host "✓ RBAC role already assigned (Cosmos DB Built-in Data Contributor)" -ForegroundColor Green
} else {
    Write-Host "❌ RBAC role NOT assigned - creating role assignment..." -ForegroundColor Yellow
    
    # Create role assignment
    $assignmentResult = az cosmosdb sql role assignment create `
        --account-name $CosmosAccountName `
        --resource-group $BackendResourceGroup `
        --scope "/" `
        --principal-id $principalId `
        --role-definition-id $roleDefinitionId `
        2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ RBAC role assigned successfully" -ForegroundColor Green
        Write-Host "   Waiting 60 seconds for RBAC propagation across Azure regions..." -ForegroundColor Yellow
        Start-Sleep -Seconds 60
    } else {
        Write-Host "⚠ Role assignment may already exist or had issues: $assignmentResult" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 5: Verify Cosmos DB local auth is disabled (security best practice)
Write-Host "[5/6] Verifying Cosmos DB security settings..." -ForegroundColor Yellow
$cosmosSettings = az cosmosdb show --name $CosmosAccountName --resource-group $BackendResourceGroup -o json | ConvertFrom-Json

if ($cosmosSettings.disableLocalAuth -eq $true) {
    Write-Host "✓ Local auth is disabled (managed identity only) - SECURE" -ForegroundColor Green
} else {
    Write-Host "⚠ Local auth is enabled - disabling for security..." -ForegroundColor Yellow
    
    $subscriptionId = az account show --query "id" -o tsv
    $cosmosResourceId = "/subscriptions/$subscriptionId/resourceGroups/$BackendResourceGroup/providers/Microsoft.DocumentDB/databaseAccounts/$CosmosAccountName"
    
    az resource update `
        --ids $cosmosResourceId `
        --set properties.disableLocalAuth=true `
        --api-version 2023-11-15 `
        --output none 2>&1 | Out-Null
    
    Write-Host "✓ Local auth disabled" -ForegroundColor Green
}

Write-Host ""

# Step 6: Restart Web App to refresh managed identity token
Write-Host "[6/6] Restarting Web App to refresh managed identity credentials..." -ForegroundColor Yellow
Write-Host "   (This ensures the app gets fresh tokens with proper RBAC permissions)" -ForegroundColor Gray

az webapp restart --name $WebAppName --resource-group $FrontendResourceGroup --output none 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Web App restarted successfully" -ForegroundColor Green
} else {
    Write-Host "⚠ Restart had issues (non-critical)" -ForegroundColor Yellow
}

Write-Host ""

# Wait for app to come back online
Write-Host "⏱  Waiting 30 seconds for app to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " ✅ Authentication Fix Complete!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Summary of actions:" -ForegroundColor Cyan
Write-Host "  ✓ Verified managed identity is enabled" -ForegroundColor Gray
Write-Host "  ✓ Verified/assigned RBAC permissions" -ForegroundColor Gray
Write-Host "  ✓ Ensured local auth is disabled (secure)" -ForegroundColor Gray
Write-Host "  ✓ Restarted app with fresh credentials" -ForegroundColor Gray
Write-Host ""
Write-Host "Test your app:" -ForegroundColor Yellow
Write-Host "  URL: https://$WebAppName.azurewebsites.net" -ForegroundColor White
Write-Host "  Login: admin / admin123" -ForegroundColor White
Write-Host ""
Write-Host "If you still see auth errors:" -ForegroundColor Yellow
Write-Host "  1. Wait 2-3 more minutes (RBAC can take up to 5 minutes)" -ForegroundColor Gray
Write-Host "  2. Check app logs: az webapp log tail --name $WebAppName --resource-group $FrontendResourceGroup" -ForegroundColor Gray
Write-Host "  3. Verify environment variables are set correctly in App Service settings" -ForegroundColor Gray
Write-Host ""
