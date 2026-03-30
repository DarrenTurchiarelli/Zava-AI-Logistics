# =============================================================================
# Diagnose Cosmos DB Authentication Issues
# =============================================================================
# Checks all authentication-related settings for Web App → Cosmos DB
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
Write-Host " Cosmos DB Authentication Diagnostic" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Find resources if not specified
if (-not $WebAppName) {
    $webApp = az webapp list --resource-group $FrontendResourceGroup --query "[0].{name:name}" -o json 2>$null | ConvertFrom-Json
    $WebAppName = $webApp.name
}

if (-not $CosmosAccountName) {
    $cosmosAccount = az cosmosdb list --resource-group $BackendResourceGroup --query "[0].{name:name}" -o json 2>$null | ConvertFrom-Json
    $CosmosAccountName = $cosmosAccount.name
}

Write-Host "Resources:" -ForegroundColor Yellow
Write-Host "  Web App: $WebAppName" -ForegroundColor Gray
Write-Host "  Cosmos DB: $CosmosAccountName" -ForegroundColor Gray
Write-Host ""

$issues = @()
$warnings = @()

# Check 1: Managed Identity
Write-Host "[Check 1/7] Managed Identity Status..." -ForegroundColor Yellow
$identity = az webapp identity show --name $WebAppName --resource-group $FrontendResourceGroup -o json 2>$null | ConvertFrom-Json

if ($identity -and $identity.principalId) {
    Write-Host "  ✓ Managed identity is enabled" -ForegroundColor Green
    Write-Host "    Principal ID: $($identity.principalId)" -ForegroundColor Gray
    $principalId = $identity.principalId
} else {
    Write-Host "  ✗ Managed identity is NOT enabled" -ForegroundColor Red
    $issues += "Managed identity not enabled on Web App"
}
Write-Host ""

# Check 2: RBAC Role Assignment
Write-Host "[Check 2/7] RBAC Permissions..." -ForegroundColor Yellow
if ($principalId) {
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
        Write-Host "  ✓ RBAC role assigned (Cosmos DB Built-in Data Contributor)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ RBAC role NOT assigned" -ForegroundColor Red
        $issues += "Missing Cosmos DB Built-in Data Contributor role"
    }
} else {
    Write-Host "  ⊘ Cannot check (no managed identity)" -ForegroundColor Gray
}
Write-Host ""

# Check 3: Cosmos DB Local Auth Setting
Write-Host "[Check 3/7] Cosmos DB Authentication Method..." -ForegroundColor Yellow
$cosmosSettings = az cosmosdb show --name $CosmosAccountName --resource-group $BackendResourceGroup -o json 2>$null | ConvertFrom-Json

if ($cosmosSettings.disableLocalAuth -eq $true) {
    Write-Host "  ✓ Local auth disabled (managed identity only) - SECURE" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Local auth enabled (allows key-based access)" -ForegroundColor Yellow
    $warnings += "Local auth is enabled (should be disabled for production)"
}
Write-Host ""

# Check 4: App Service Environment Variables
Write-Host "[Check 4/7] App Service Environment Variables..." -ForegroundColor Yellow
$appSettings = az webapp config appsettings list --name $WebAppName --resource-group $FrontendResourceGroup -o json 2>$null | ConvertFrom-Json

$requiredSettings = @(
    @{ Name = "COSMOS_DB_ENDPOINT"; Description = "Cosmos DB endpoint URL" },
    @{ Name = "COSMOS_DB_DATABASE_NAME"; Description = "Database name" },
    @{ Name = "USE_MANAGED_IDENTITY"; Description = "Must be 'true' for Azure" }
)

foreach ($setting in $requiredSettings) {
    $found = $appSettings | Where-Object { $_.name -eq $setting.Name }
    
    if ($found) {
        Write-Host "  ✓ $($setting.Name) = $($found.value)" -ForegroundColor Green
        
        # Check specific values
        if ($setting.Name -eq "USE_MANAGED_IDENTITY" -and $found.value -ne "true") {
            Write-Host "    ⚠ Should be 'true' for Azure deployment" -ForegroundColor Yellow
            $warnings += "USE_MANAGED_IDENTITY should be 'true'"
        }
    } else {
        Write-Host "  ✗ $($setting.Name) is NOT set" -ForegroundColor Red
        $issues += "Missing environment variable: $($setting.Name)"
    }
}

# Check for unwanted settings that would cause key-based auth
$unwantedSettings = @("COSMOS_DB_KEY", "COSMOS_CONNECTION_STRING")
foreach ($unwanted in $unwantedSettings) {
    $found = $appSettings | Where-Object { $_.name -eq $unwanted }
    if ($found) {
        Write-Host "  ⚠ $unwanted is set (not needed with managed identity)" -ForegroundColor Yellow
        $warnings += "$unwanted should be removed for managed identity auth"
    }
}
Write-Host ""

# Check 5: Web App Runtime Status
Write-Host "[Check 5/7] Web App Runtime Status..." -ForegroundColor Yellow
$webAppDetails = az webapp show --name $WebAppName --resource-group $FrontendResourceGroup -o json 2>$null | ConvertFrom-Json

if ($webAppDetails.state -eq "Running") {
    Write-Host "  ✓ Web App is running" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Web App state: $($webAppDetails.state)" -ForegroundColor Yellow
    $warnings += "Web App is not in Running state"
}
Write-Host ""

# Check 6: Network Connectivity
Write-Host "[Check 6/7] Network Connectivity..." -ForegroundColor Yellow
$cosmosEndpoint = $cosmosSettings.documentEndpoint

if ($cosmosEndpoint) {
    Write-Host "  ✓ Cosmos DB endpoint: $cosmosEndpoint" -ForegroundColor Green
    
    # Check if public access is enabled
    if ($cosmosSettings.publicNetworkAccess -eq "Enabled") {
        Write-Host "  ✓ Public network access enabled" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Public network access: $($cosmosSettings.publicNetworkAccess)" -ForegroundColor Yellow
        $warnings += "Public network access may be restricted"
    }
} else {
    Write-Host "  ✗ Cannot determine Cosmos DB endpoint" -ForegroundColor Red
}
Write-Host ""

# Check 7: Recent Restart (for token refresh)
Write-Host "[Check 7/7] Recent Configuration Changes..." -ForegroundColor Yellow
Write-Host "  ℹ  If RBAC was just assigned, app needs restart to get fresh tokens" -ForegroundColor Gray
Write-Host "  ℹ  RBAC propagation can take 2-5 minutes across Azure regions" -ForegroundColor Gray
Write-Host ""

# Summary
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Diagnostic Summary" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

if ($issues.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "✅ All checks passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "If you're still seeing auth errors:" -ForegroundColor Yellow
    Write-Host "  • Wait 2-3 more minutes for RBAC propagation" -ForegroundColor Gray
    Write-Host "  • Restart the web app: az webapp restart --name $WebAppName --resource-group $FrontendResourceGroup" -ForegroundColor Gray
    Write-Host "  • Check app logs: az webapp log tail --name $WebAppName --resource-group $FrontendResourceGroup" -ForegroundColor Gray
} else {
    if ($issues.Count -gt 0) {
        Write-Host "❌ CRITICAL ISSUES ($($issues.Count)):" -ForegroundColor Red
        foreach ($issue in $issues) {
            Write-Host "  • $issue" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "⚠ WARNINGS ($($warnings.Count)):" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  • $warning" -ForegroundColor Yellow
        }
        Write-Host ""
    }
    
    Write-Host "Recommended fix:" -ForegroundColor Cyan
    Write-Host "  Run: .\Scripts\fix_cosmos_auth.ps1" -ForegroundColor White
    Write-Host ""
}
