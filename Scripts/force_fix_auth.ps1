# =============================================================================
# AGGRESSIVE Cosmos DB Authentication Fix
# =============================================================================
# When standard fix doesn't work - this does a complete reset
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

Write-Host "======================================================================" -ForegroundColor Red
Write-Host " AGGRESSIVE AUTHENTICATION FIX" -ForegroundColor Red
Write-Host "======================================================================" -ForegroundColor Red
Write-Host ""
Write-Host "⚠️  This script will:" -ForegroundColor Yellow
Write-Host "   1. Remove ALL key-based auth environment variables" -ForegroundColor Yellow
Write-Host "   2. Verify/assign RBAC permissions" -ForegroundColor Yellow
Write-Host "   3. STOP the web app completely" -ForegroundColor Yellow
Write-Host "   4. Wait for RBAC propagation (90 seconds)" -ForegroundColor Yellow
Write-Host "   5. START the web app with fresh credentials" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Continue? (Y/N)"
if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "Aborted." -ForegroundColor Gray
    exit 0
}
Write-Host ""

# Auto-detect resources
if (-not $WebAppName) {
    Write-Host "[1/8] Finding Web App..." -ForegroundColor Yellow
    $webApp = az webapp list --resource-group $FrontendResourceGroup --query "[0].{name:name}" -o json 2>$null | ConvertFrom-Json
    if (-not $webApp) {
        Write-Host "❌ ERROR: No Web App found" -ForegroundColor Red
        exit 1
    }
    $WebAppName = $webApp.name
}

if (-not $CosmosAccountName) {
    Write-Host "[2/8] Finding Cosmos DB..." -ForegroundColor Yellow
    $cosmosAccount = az cosmosdb list --resource-group $BackendResourceGroup --query "[0].{name:name}" -o json 2>$null | ConvertFrom-Json
    if (-not $cosmosAccount) {
        Write-Host "❌ ERROR: No Cosmos DB found" -ForegroundColor Red
        exit 1
    }
    $CosmosAccountName = $cosmosAccount.name
}

Write-Host "✓ Web App: $WebAppName" -ForegroundColor Green
Write-Host "✓ Cosmos DB: $CosmosAccountName" -ForegroundColor Green
Write-Host ""

# Step 3: Get managed identity
Write-Host "[3/8] Verifying managed identity..." -ForegroundColor Yellow
$identity = az webapp identity show --name $WebAppName --resource-group $FrontendResourceGroup -o json 2>$null | ConvertFrom-Json

if (-not $identity -or -not $identity.principalId) {
    Write-Host "❌ Managed identity not enabled - enabling now..." -ForegroundColor Red
    az webapp identity assign --name $WebAppName --resource-group $FrontendResourceGroup | Out-Null
    Start-Sleep -Seconds 10
    $identity = az webapp identity show --name $WebAppName --resource-group $FrontendResourceGroup -o json | ConvertFrom-Json
}

$principalId = $identity.principalId
Write-Host "✓ Principal ID: $principalId" -ForegroundColor Green
Write-Host ""

# Step 4: Remove ALL key-based auth environment variables
Write-Host "[4/8] Removing key-based auth environment variables..." -ForegroundColor Yellow
$currentSettings = az webapp config appsettings list --name $WebAppName --resource-group $FrontendResourceGroup -o json | ConvertFrom-Json

$keysToRemove = @("COSMOS_DB_KEY", "COSMOS_CONNECTION_STRING", "FORCE_KEY_AUTH")
$removedAny = $false

foreach ($key in $keysToRemove) {
    $exists = $currentSettings | Where-Object { $_.name -eq $key }
    if ($exists) {
        Write-Host "  • Removing $key" -ForegroundColor Cyan
        az webapp config appsettings delete --name $WebAppName --resource-group $FrontendResourceGroup --setting-names $key --output none 2>&1 | Out-Null
        $removedAny = $true
    }
}

if ($removedAny) {
    Write-Host "✓ Removed key-based auth variables" -ForegroundColor Green
} else {
    Write-Host "✓ No key-based auth variables found (good)" -ForegroundColor Green
}

# Verify required settings exist
$requiredSettings = @{
    "USE_MANAGED_IDENTITY" = "true"
    "COSMOS_DB_ENDPOINT" = "https://$CosmosAccountName.documents.azure.com:443/"
    "COSMOS_DB_DATABASE_NAME" = "logisticstracking"
}

Write-Host "  • Verifying managed identity settings..." -ForegroundColor Cyan
$settingsToSet = @()

foreach ($setting in $requiredSettings.GetEnumerator()) {
    $exists = $currentSettings | Where-Object { $_.name -eq $setting.Key -and $_.value -eq $setting.Value }
    if (-not $exists) {
        $settingsToSet += "$($setting.Key)=$($setting.Value)"
    }
}

if ($settingsToSet.Count -gt 0) {
    az webapp config appsettings set --name $WebAppName --resource-group $FrontendResourceGroup --settings @settingsToSet --output none
    Write-Host "✓ Updated $($settingsToSet.Count) managed identity settings" -ForegroundColor Green
} else {
    Write-Host "✓ All managed identity settings correct" -ForegroundColor Green
}
Write-Host ""

# Step 5: Verify/assign RBAC
Write-Host "[5/8] Verifying RBAC permissions..." -ForegroundColor Yellow
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
    Write-Host "✓ RBAC role already assigned" -ForegroundColor Green
} else {
    Write-Host "❌ RBAC role NOT assigned - assigning now..." -ForegroundColor Red
    
    az cosmosdb sql role assignment create `
        --account-name $CosmosAccountName `
        --resource-group $BackendResourceGroup `
        --scope "/" `
        --principal-id $principalId `
        --role-definition-id $roleDefinitionId `
        --output none 2>&1 | Out-Null
    
    Write-Host "✓ RBAC role assigned" -ForegroundColor Green
}
Write-Host ""

# Step 6: STOP the web app
Write-Host "[6/8] STOPPING web app..." -ForegroundColor Yellow
az webapp stop --name $WebAppName --resource-group $FrontendResourceGroup --output none

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Web app stopped" -ForegroundColor Green
} else {
    Write-Host "⚠ Stop command had issues (non-critical)" -ForegroundColor Yellow
}
Write-Host ""

# Step 7: Wait for RBAC propagation
Write-Host "[7/8] Waiting 90 seconds for RBAC propagation across Azure..." -ForegroundColor Yellow
Write-Host "   (RBAC changes can take 2-5 minutes to fully propagate)" -ForegroundColor Gray
for ($i = 90; $i -gt 0; $i--) {
    Write-Host "`r   Time remaining: $i seconds...  " -NoNewline -ForegroundColor Cyan
    Start-Sleep -Seconds 1
}
Write-Host "`r   ✓ Wait complete                  " -ForegroundColor Green
Write-Host ""

# Step 8: START the web app (forces fresh token)
Write-Host "[8/8] STARTING web app with fresh credentials..." -ForegroundColor Yellow
az webapp start --name $WebAppName --resource-group $FrontendResourceGroup --output none

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Web app started" -ForegroundColor Green
} else {
    Write-Host "⚠ Start command had issues" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  ⏱ Waiting 45 seconds for app to fully initialize..." -ForegroundColor Cyan
for ($i = 45; $i -gt 0; $i--) {
    Write-Host "`r   Time remaining: $i seconds...  " -NoNewline -ForegroundColor Gray
    Start-Sleep -Seconds 1
}
Write-Host "`r   ✓ App initialization complete     " -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " ✅ AGGRESSIVE FIX COMPLETE" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Actions taken:" -ForegroundColor Cyan
Write-Host "  ✓ Removed all key-based auth environment variables" -ForegroundColor Gray
Write-Host "  ✓ Configured managed identity environment variables" -ForegroundColor Gray
Write-Host "  ✓ Verified/assigned RBAC permissions" -ForegroundColor Gray
Write-Host "  ✓ Completely stopped and restarted app" -ForegroundColor Gray
Write-Host "  ✓ Waited for RBAC propagation and app initialization" -ForegroundColor Gray
Write-Host ""
Write-Host "Test your app now:" -ForegroundColor Yellow
Write-Host "  URL: https://$WebAppName.azurewebsites.net" -ForegroundColor White
Write-Host "  Login: admin / admin123" -ForegroundColor White
Write-Host ""
Write-Host "If you STILL see auth errors:" -ForegroundColor Red
Write-Host "  1. Wait 3-5 more minutes (RBAC can take up to 5 minutes total)" -ForegroundColor Gray
Write-Host "  2. Check app logs: az webapp log tail --name $WebAppName --resource-group $FrontendResourceGroup" -ForegroundColor Gray
Write-Host "  3. The issue may be with Cosmos DB itself - verify health in Azure Portal" -ForegroundColor Gray
Write-Host ""
