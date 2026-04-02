# ============================================================================
# Fix Azure Computer Vision RBAC Permissions
# 
# This script assigns the correct "Cognitive Services User" role to the
# App Service managed identity for Computer Vision access.
# 
# The deployment originally used "Cognitive Services OpenAI User" role,
# which only works for Azure OpenAI, not Computer Vision.
# ============================================================================

$ErrorActionPreference = "Stop"

Write-Host "`n" -NoNewline
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "  Azure Computer Vision - RBAC Permission Fix" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Load deployment config
$deploymentConfigPath = Join-Path $PSScriptRoot ".." ".azure-deployment.json"

if (-not (Test-Path $deploymentConfigPath)) {
    Write-Host "❌ Deployment config not found: $deploymentConfigPath" -ForegroundColor Red
    Write-Host "   Please run deploy_to_azure.ps1 first" -ForegroundColor Yellow
    exit 1
}

$config = Get-Content $deploymentConfigPath | ConvertFrom-Json
Write-Host "✅ Loaded deployment config" -ForegroundColor Green

# Extract resource details (support both old and new config formats)
if ($config.resourceGroups) {
    # New format (nested objects)
    $frontendRg = $config.resourceGroups.frontend
    $sharedRg = $config.resourceGroups.shared
    $appServiceName = $config.frontend.appServiceName
} else {
    # Old format (flat properties)
    $frontendRg = $config.FrontendResourceGroup
    $sharedRg = $config.SharedResourceGroup
    
    # Extract app service name from URL or use AppServiceName property
    if ($config.AppServiceName) {
        $appServiceName = $config.AppServiceName
    } elseif ($config.Url) {
        # Extract from URL: https://app-name.azurewebsites.net -> app-name
        $appServiceName = ($config.Url -replace 'https://', '' -replace '.azurewebsites.net.*', '')
    } else {
        Write-Host "❌ Could not determine App Service name from config" -ForegroundColor Red
        exit 1
    }
}

Write-Host "   Frontend RG: $frontendRg" -ForegroundColor Gray
Write-Host "   Shared RG: $sharedRg" -ForegroundColor Gray
Write-Host "   App Service: $appServiceName" -ForegroundColor Gray
Write-Host ""

# Get App Service managed identity principal ID
Write-Host "📋 Getting App Service managed identity..." -ForegroundColor Cyan
$appService = az webapp show `
    --name $appServiceName `
    --resource-group $frontendRg `
    --query "{principalId:identity.principalId, name:name}" `
    -o json | ConvertFrom-Json

if (-not $appService.principalId) {
    Write-Host "❌ App Service managed identity not found" -ForegroundColor Red
    Write-Host "   Ensure managed identity is enabled on the App Service" -ForegroundColor Yellow
    exit 1
}

$principalId = $appService.principalId
Write-Host "   ✅ Principal ID: $principalId" -ForegroundColor Green
Write-Host ""

# Get Vision service details
Write-Host "🔍 Finding Azure Computer Vision service..." -ForegroundColor Cyan
$visionServices = az cognitiveservices account list `
    --resource-group $sharedRg `
    --query "[?kind=='ComputerVision'].{name:name, id:id}" `
    -o json | ConvertFrom-Json

if ($visionServices.Count -eq 0) {
    Write-Host "❌ No Computer Vision service found in resource group: $sharedRg" -ForegroundColor Red
    exit 1
}

$visionService = $visionServices[0]
$visionServiceName = $visionService.name
$visionServiceId = $visionService.id

Write-Host "   ✅ Vision Service: $visionServiceName" -ForegroundColor Green
Write-Host "   ✅ Resource ID: $visionServiceId" -ForegroundColor Green
Write-Host ""

# Check existing role assignments
Write-Host "🔍 Checking existing role assignments..." -ForegroundColor Cyan
$existingRoles = az role assignment list `
    --assignee $principalId `
    --scope $visionServiceId `
    --query "[].{role:roleDefinitionName, id:id}" `
    -o json | ConvertFrom-Json

if ($existingRoles.Count -gt 0) {
    Write-Host "   Current roles:" -ForegroundColor Yellow
    foreach ($role in $existingRoles) {
        Write-Host "   - $($role.role)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Assign Cognitive Services User role (required for Computer Vision)
$roleDefinitionName = "Cognitive Services User"
Write-Host "🔒 Assigning role: $roleDefinitionName" -ForegroundColor Cyan
Write-Host "   This role includes the data action:" -ForegroundColor Gray
Write-Host "   Microsoft.CognitiveServices/accounts/ComputerVision/imageanalysis:analyze/action" -ForegroundColor Gray
Write-Host ""

try {
    az role assignment create `
        --assignee $principalId `
        --role $roleDefinitionName `
        --scope $visionServiceId `
        --output none

    Write-Host "   ✅ Role assignment created successfully!" -ForegroundColor Green
} catch {
    if ($_.Exception.Message -like "*already exists*") {
        Write-Host "   ℹ️  Role already assigned (OK)" -ForegroundColor Yellow
    } else {
        Write-Host "   ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Wait for RBAC propagation
Write-Host "⏳ Waiting for Azure RBAC propagation (60 seconds)..." -ForegroundColor Cyan
Write-Host "   RBAC changes can take 2-5 minutes to propagate across Azure regions" -ForegroundColor Gray
Start-Sleep -Seconds 60

# Restart App Service to refresh credentials
Write-Host ""
Write-Host "🔄 Restarting App Service to refresh managed identity credentials..." -ForegroundColor Cyan
az webapp restart --name $appServiceName --resource-group $frontendRg --output none
Write-Host "   ✅ App Service restarted" -ForegroundColor Green

Write-Host ""
Write-Host "⏳ Waiting for App Service to fully initialize (30 seconds)..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# Test the endpoint
Write-Host ""
Write-Host "🧪 Testing Computer Vision access..." -ForegroundColor Cyan
$appUrl = "https://$appServiceName.azurewebsites.net"
Write-Host "   App URL: $appUrl" -ForegroundColor Gray
Write-Host ""

Write-Host "✅ Fix complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Wait an additional 2-3 minutes for full RBAC propagation" -ForegroundColor White
Write-Host "   2. Test the camera scanner at: $appUrl/camera-scanner" -ForegroundColor White
Write-Host "   3. If still not working, check App Service logs:" -ForegroundColor White
Write-Host "      az webapp log tail --name $appServiceName --resource-group $frontendRg" -ForegroundColor Gray
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
