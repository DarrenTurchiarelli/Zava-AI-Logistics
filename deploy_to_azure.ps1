# =============================================================================
# Deploy Zava to Azure with Complete Infrastructure via Bicep
# =============================================================================

param(
    [string]$ResourceGroup = "RG-Zava-Logistics",
    [string]$Location = "australiaeast",
    [string]$Environment = "dev",
    [string]$Sku = "B2",
    [switch]$Force,
    [switch]$SkipInfrastructure,
    [switch]$CodeOnly
)

$deploymentConfigFile = ".azure-deployment.json"
$bicepTemplate = "infra/main.bicep"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Zava - Complete Azure Infrastructure Deployment" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Check for existing deployment
$existingDeployment = $null
$isRedeployment = $false
$WebAppName = ""

if ((Test-Path $deploymentConfigFile) -and -not $Force) {
    Write-Host "[0/7] Found existing deployment configuration..." -ForegroundColor Yellow
    try {
        $existingDeployment = Get-Content $deploymentConfigFile -Raw | ConvertFrom-Json
        $WebAppName = $existingDeployment.AppServiceName
        $isRedeployment = $true

        Write-Host "✓ Will redeploy to existing App Service: $WebAppName" -ForegroundColor Green
        Write-Host "  Resource Group: $($existingDeployment.ResourceGroup)" -ForegroundColor Gray
    } catch {
        Write-Host "⚠ Could not read existing deployment config" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Check if logged in
Write-Host "[1/7] Checking Azure login status..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "✗ Not logged in to Azure. Running 'az login'..." -ForegroundColor Red
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Host "✓ Logged in as: $($account.user.name)" -ForegroundColor Green
Write-Host "✓ Subscription: $($account.name)" -ForegroundColor Green
Write-Host ""

# Register Required Resource Providers
Write-Host "[1.5/7] Registering required Azure resource providers..." -ForegroundColor Yellow
$requiredProviders = @(
    "Microsoft.DocumentDB",              # Cosmos DB
    "Microsoft.CognitiveServices",       # Azure AI, Speech, Vision
    "Microsoft.Maps",                    # Azure Maps
    "Microsoft.Web",                     # App Service
    "Microsoft.Insights",                # Application Insights
    "Microsoft.OperationalInsights",     # Log Analytics
    "Microsoft.Storage",                 # Storage Account
    "Microsoft.MachineLearningServices"  # AI Hub & Project
)

$registrationNeeded = $false
foreach ($provider in $requiredProviders) {
    $providerStatus = az provider show --namespace $provider --query "registrationState" -o tsv 2>$null

    if ($providerStatus -eq "Registered") {
        Write-Host "  ✓ $provider" -ForegroundColor Green
    } elseif ($providerStatus -eq "Registering") {
        Write-Host "  ⏳ $provider (registering...)" -ForegroundColor Yellow
        $registrationNeeded = $true
    } else {
        Write-Host "  ⚙ Registering $provider..." -ForegroundColor Cyan
        az provider register --namespace $provider --wait 2>$null
        $registrationNeeded = $true
    }
}

if ($registrationNeeded) {
    Write-Host ""
    Write-Host "  ⏱ Waiting for provider registration to complete (this may take 1-2 minutes)..." -ForegroundColor Yellow

    # Wait for all providers to be registered
    $maxWaitTime = 180  # 3 minutes max
    $waitInterval = 10  # Check every 10 seconds
    $elapsed = 0
    $allRegistered = $false

    while (-not $allRegistered -and $elapsed -lt $maxWaitTime) {
        Start-Sleep -Seconds $waitInterval
        $elapsed += $waitInterval

        $allRegistered = $true
        foreach ($provider in $requiredProviders) {
            $status = az provider show --namespace $provider --query "registrationState" -o tsv 2>$null
            if ($status -ne "Registered") {
                $allRegistered = $false
                break
            }
        }

        if (-not $allRegistered) {
            Write-Host "  ⏳ Still waiting... ($elapsed seconds)" -ForegroundColor Gray
        }
    }

    if ($allRegistered) {
        Write-Host "  ✓ All resource providers registered successfully" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Some providers still registering. Deployment will continue..." -ForegroundColor Yellow
        Write-Host "    (Azure will wait for provider registration automatically)" -ForegroundColor Gray
    }
} else {
    Write-Host "  ✓ All required resource providers already registered" -ForegroundColor Green
}
Write-Host ""

# Create Resource Group
Write-Host "[2/7] Creating/Verifying Resource Group: $ResourceGroup..." -ForegroundColor Yellow
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -eq "true") {
    Write-Host "✓ Resource Group exists" -ForegroundColor Green
} else {
    az group create --name $ResourceGroup --location $Location --output none
    Write-Host "✓ Resource Group created" -ForegroundColor Green
}
Write-Host ""

# Deploy Bicep Infrastructure
if (-not $SkipInfrastructure -and -not $CodeOnly) {
    Write-Host "[3/7] Deploying complete infrastructure via Bicep..." -ForegroundColor Yellow
    Write-Host "  📦 This will create:" -ForegroundColor Cyan
    Write-Host "     • Cosmos DB (serverless) with all containers" -ForegroundColor Gray
    Write-Host "     • Azure AI Hub & Project for Foundry agents" -ForegroundColor Gray
    Write-Host "     • Azure Maps, Speech, Vision services" -ForegroundColor Gray
    Write-Host "     • App Service & Plan (Linux Python 3.11)" -ForegroundColor Gray
    Write-Host "     • Application Insights & Log Analytics" -ForegroundColor Gray
    Write-Host "     • Storage Account for AI Hub" -ForegroundColor Gray
    Write-Host "     • RBAC role assignments (managed identity)" -ForegroundColor Gray
    Write-Host "  ⏱ This may take 5-10 minutes..." -ForegroundColor Gray
    Write-Host ""

    if (-not (Test-Path $bicepTemplate)) {
        Write-Host "  ✗ Bicep template not found: $bicepTemplate" -ForegroundColor Red
        Write-Host "  Please ensure the infra/main.bicep file exists" -ForegroundColor Red
        exit 1
    }

    # Deploy Bicep template
    $deploymentName = "zava-deployment-$(Get-Date -Format 'yyyyMMddHHmmss')"

    Write-Host "  🚀 Starting Bicep deployment: $deploymentName" -ForegroundColor Cyan

    # Note: Not using 2>&1 to avoid mixing errors with JSON output
    $bicepOutput = az deployment group create `
        --name $deploymentName `
        --resource-group $ResourceGroup `
        --template-file $bicepTemplate `
        --parameters location=$Location environment=$Environment appServiceSku=$Sku `
        --query properties.outputs `
        --output json

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Infrastructure deployment failed" -ForegroundColor Red
        Write-Host "  Run 'az deployment group show --name $deploymentName --resource-group $ResourceGroup' for details" -ForegroundColor Yellow
        exit 1
    }

    # Parse JSON output
    try {
        $bicepOutputJson = $bicepOutput | ConvertFrom-Json
    } catch {
        Write-Host "  ✗ Failed to parse deployment output" -ForegroundColor Red
        Write-Host "  Output was: $bicepOutput" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Attempting to retrieve deployment outputs manually..." -ForegroundColor Yellow

        $bicepOutputJson = az deployment group show `
            --name $deploymentName `
            --resource-group $ResourceGroup `
            --query properties.outputs `
            --output json | ConvertFrom-Json
    }

    Write-Host "  ✓ Infrastructure deployed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  📋 Deployment Details:" -ForegroundColor Cyan
    Write-Host "     App Service: $($bicepOutputJson.appServiceName.value)" -ForegroundColor Gray
    Write-Host "     URL: $($bicepOutputJson.appServiceUrl.value)" -ForegroundColor Gray
    Write-Host "     Cosmos DB: $($bicepOutputJson.cosmosDbAccountName.value)" -ForegroundColor Gray
    Write-Host "     AI Hub: $($bicepOutputJson.aiHubName.value)" -ForegroundColor Gray
    Write-Host "     AI Project: $($bicepOutputJson.aiProjectName.value)" -ForegroundColor Gray
    Write-Host ""

    # Store deployment info
    $WebAppName = $bicepOutputJson.appServiceName.value

    # Validate we got the app name
    if (-not $WebAppName) {
        Write-Host "  ✗ Failed to retrieve App Service name from deployment" -ForegroundColor Red
        Write-Host "  Please check the Bicep template outputs" -ForegroundColor Yellow
        exit 1
    }

} else {
    if ($CodeOnly) {
        Write-Host "[3/7] Skipping infrastructure deployment (-CodeOnly flag)" -ForegroundColor Yellow
    } else {
        Write-Host "[3/7] Skipping infrastructure deployment (-SkipInfrastructure flag)" -ForegroundColor Yellow
    }

    if (-not $WebAppName) {
        Write-Host "  ✗ No existing deployment found. Cannot proceed with code-only deployment." -ForegroundColor Red
        Write-Host "  Remove -CodeOnly or -SkipInfrastructure flag for first deployment" -ForegroundColor Yellow
        Write-Host "  Or ensure .azure-deployment.json exists with AppServiceName field" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "  ✓ Using existing App Service: $WebAppName" -ForegroundColor Green
    Write-Host ""
}

# Get Web App details
Write-Host "[4/7] Retrieving Web App configuration..." -ForegroundColor Yellow

if (-not $WebAppName) {
    Write-Host "  ✗ WebAppName is empty. This is a script error." -ForegroundColor Red
    Write-Host "  Please report this issue with the deployment output above" -ForegroundColor Yellow
    exit 1
}

Write-Host "  Checking App Service: $WebAppName" -ForegroundColor Gray
$webApp = az webapp show --name $WebAppName --resource-group $ResourceGroup --output json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Could not retrieve Web App '$WebAppName'" -ForegroundColor Red
    Write-Host "  Error: $webApp" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Troubleshooting:" -ForegroundColor Cyan
    Write-Host "    - Verify app service exists: az webapp list --resource-group $ResourceGroup" -ForegroundColor Gray
    Write-Host "    - Check resource group: az group show --name $ResourceGroup" -ForegroundColor Gray
    exit 1
}
$webApp = $webApp | ConvertFrom-Json
Write-Host "  ✓ Web App Status: $($webApp.state)" -ForegroundColor Green
Write-Host "  ✓ Default Hostname: $($webApp.defaultHostName)" -ForegroundColor Green
Write-Host ""

# Configure Additional App Settings (Agent IDs from .env)
Write-Host "[5/7] Configuring application settings from .env..." -ForegroundColor Yellow

$additionalSettings = @()

# Read agent IDs and depot addresses from .env
if (Test-Path ".env") {
    Write-Host "  Reading agent IDs and depot addresses from .env..." -ForegroundColor Gray

    $agentIds = @{}
    $depots = @{}

    Get-Content .env | ForEach-Object {
        # Agent IDs
        if ($_ -match '^(CUSTOMER_SERVICE_AGENT_ID|FRAUD_RISK_AGENT_ID|IDENTITY_AGENT_ID|DISPATCHER_AGENT_ID|PARCEL_INTAKE_AGENT_ID|SORTING_FACILITY_AGENT_ID|DELIVERY_COORDINATION_AGENT_ID|OPTIMIZATION_AGENT_ID|DRIVER_AGENT_ID)\s*=\s*"?([^"]+)"?') {
            $agentIds[$matches[1]] = $matches[2]
        }
        # Depot addresses
        if ($_ -match '^(DEPOT_NSW|DEPOT_VIC|DEPOT_QLD|DEPOT_SA|DEPOT_WA|DEPOT_TAS|DEPOT_ACT|DEPOT_NT)\s*=\s*"?([^"]+)"?') {
            $depots[$matches[1]] = $matches[2]
        }
    }

    # Add agent IDs to settings
    foreach ($key in $agentIds.Keys) {
        $additionalSettings += "$key=$($agentIds[$key])"
    }

    if ($agentIds.Count -gt 0) {
        Write-Host "  ✓ Found $($agentIds.Count) agent ID(s)" -ForegroundColor Green
    }

    # Add depot addresses
    foreach ($key in $depots.Keys) {
        $additionalSettings += "$key=$($depots[$key])"
    }

    if ($depots.Count -gt 0) {
        Write-Host "  ✓ Found $($depots.Count) depot address(es)" -ForegroundColor Green
    }
}

# Apply additional settings if any
if ($additionalSettings.Count -gt 0) {
    az webapp config appsettings set `
        --name $WebAppName `
        --resource-group $ResourceGroup `
        --settings $additionalSettings `
        --output none
    Write-Host "✓ Agent IDs and depot addresses configured" -ForegroundColor Green
} else {
    Write-Host "⚠ No agent IDs found in .env file" -ForegroundColor Yellow
    Write-Host "  You'll need to create agents in Azure AI Foundry and update app settings" -ForegroundColor Gray
}
Write-Host ""

# Deploy Application Code
Write-Host "[6/7] Deploying application code..." -ForegroundColor Yellow
Write-Host "  This may take 3-5 minutes..." -ForegroundColor Gray

# Create a deployment ZIP (excluding unnecessary files)
$tempZip = "$env:TEMP\dt-logistics-deploy.zip"
if (Test-Path $tempZip) { Remove-Item $tempZip -Force }

Write-Host "  Creating deployment package..." -ForegroundColor Gray
Compress-Archive -Path * -DestinationPath $tempZip -Force -ErrorAction SilentlyContinue

# Deploy ZIP
Write-Host "  Uploading to Azure..." -ForegroundColor Gray
$deployResult = az webapp deployment source config-zip `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --src $tempZip `
    --timeout 600 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Code deployment failed: $deployResult" -ForegroundColor Red
} else {
    Write-Host "✓ Application code deployed" -ForegroundColor Green
}

Remove-Item $tempZip -Force
Write-Host ""

# Post-Deployment Tasks
Write-Host "[7/7] Running post-deployment tasks..." -ForegroundColor Yellow

# Task 1: Wait for app to be ready
Write-Host "  ⏱  Waiting for app to initialize (30 seconds)..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# Task 2: Test endpoint
Write-Host "  🔍 Testing application endpoint..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "https://$($webApp.defaultHostName)" -Method Get -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ Application is responding" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ Application not yet responding (may need more time to start)" -ForegroundColor Yellow
    Write-Host "    Check logs with: az webapp log tail --name $WebAppName --resource-group $ResourceGroup" -ForegroundColor Gray
}

# Task 3: Initialize default users
Write-Host "  👤 Initializing default user accounts..." -ForegroundColor Cyan
try {
    # Check if Python is available
    if (Get-Command python -ErrorAction SilentlyContinue) {
        # Run setup_users.py to create default accounts
        $setupOutput = python utils/setup/setup_users.py 2>&1
        if ($LASTEXITCODE -eq 0 -and $setupOutput -match "SUCCESS") {
            Write-Host "  ✓ Default users created successfully" -ForegroundColor Green
            Write-Host "    Login at: https://$($webApp.defaultHostName)/login" -ForegroundColor Gray
            Write-Host "    Username: admin | Password: admin123" -ForegroundColor Gray
        } else {
            Write-Host "  ⚠ User initialization may have failed" -ForegroundColor Yellow
            Write-Host "    Run manually: python utils/setup/setup_users.py" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Python not found - skipping user initialization" -ForegroundColor Yellow
        Write-Host "    Users will be auto-created on first login attempt" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠ Could not initialize users: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "    Users will be auto-created on first login attempt" -ForegroundColor Gray
}

Write-Host "✓ Post-deployment tasks completed" -ForegroundColor Green
Write-Host ""

# Save deployment configuration
$deploymentInfo = @{
    AppServiceName = $WebAppName
    ResourceGroup = $ResourceGroup
    Location = $Location
    Environment = $Environment
    Sku = $Sku
    DeploymentDate = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Url = "https://$($webApp.defaultHostName)"
}

$deploymentInfo | ConvertTo-Json | Set-Content $deploymentConfigFile
Write-Host "✓ Deployment configuration saved to $deploymentConfigFile" -ForegroundColor Green
Write-Host ""

# Final Output
$url = "https://$($webApp.defaultHostName)"

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application URL: $url" -ForegroundColor Cyan
Write-Host ""
Write-Host "Default Login Credentials:" -ForegroundColor Yellow
Write-Host "  Username: admin" -ForegroundColor White
Write-Host "  Password: admin123" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Visit: $url" -ForegroundColor White
Write-Host "  2. The app will auto-initialize users on first startup" -ForegroundColor White
Write-Host "  3. View logs: az webapp log tail --name $WebAppName --resource-group $ResourceGroup" -ForegroundColor White
Write-Host "  4. Monitor in portal: https://portal.azure.com" -ForegroundColor White
Write-Host ""
Write-Host "To redeploy code only (skip infrastructure):" -ForegroundColor Cyan
Write-Host "  .\deploy_to_azure_new.ps1 --CodeOnly" -ForegroundColor White
Write-Host ""
Write-Host "To force complete redeployment:" -ForegroundColor Cyan
Write-Host "  .\deploy_to_azure_new.ps1 --Force" -ForegroundColor White
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan

# Copy URL to clipboard
$url | Set-Clipboard
Write-Host "✓ URL copied to clipboard!" -ForegroundColor Green
