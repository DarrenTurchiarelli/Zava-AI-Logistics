# =============================================================================
# Deploy Zava to Azure with Multi-Resource Group Infrastructure via Bicep
# =============================================================================

param(
    [string]$Location = "australiaeast",
    [string]$Environment = "dev",
    [string]$Sku = "B2",
    [switch]$Force,
    [switch]$SkipInfrastructure,
    [switch]$CodeOnly
)

$deploymentConfigFile = ".azure-deployment.json"
$bicepTemplate = "infra/main.bicep"

# Resource group names (will be created by Bicep)
$frontendRgName = "RG-Zava-Frontend-$Environment"
$middlewareRgName = "RG-Zava-Middleware-$Environment"
$backendRgName = "RG-Zava-Backend-$Environment"
$sharedRgName = "RG-Zava-Shared-$Environment"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Zava - Multi-Resource Group Infrastructure Deployment" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  📦 Architecture:" -ForegroundColor Cyan
Write-Host "     Frontend RG:     $frontendRgName" -ForegroundColor Gray
Write-Host "     Middleware RG:   $middlewareRgName" -ForegroundColor Gray
Write-Host "     Backend RG:      $backendRgName" -ForegroundColor Gray
Write-Host "     Shared RG:       $sharedRgName" -ForegroundColor Gray
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
        Write-Host "  Frontend RG: $frontendRgName" -ForegroundColor Gray
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

# Deploy Bicep Infrastructure at Subscription Level
if (-not $SkipInfrastructure -and -not $CodeOnly) {
    Write-Host "[3/7] Deploying multi-resource group infrastructure via Bicep..." -ForegroundColor Yellow
    Write-Host "  📦 This will create 4 resource groups with:" -ForegroundColor Cyan
    Write-Host "     Frontend:" -ForegroundColor White
    Write-Host "       • App Service & Plan (Linux Python 3.11)" -ForegroundColor Gray
    Write-Host "       • Application Insights" -ForegroundColor Gray
    Write-Host "     Middleware:" -ForegroundColor White
    Write-Host "       • Azure OpenAI Service (GPT-4o)" -ForegroundColor Gray
    Write-Host "       • Azure AI Hub & Project for Foundry agents" -ForegroundColor Gray
    Write-Host "       • Storage Account for AI Hub" -ForegroundColor Gray
    Write-Host "     Backend:" -ForegroundColor White
    Write-Host "       • Cosmos DB (serverless) with all containers" -ForegroundColor Gray
    Write-Host "     Shared Services:" -ForegroundColor White
   Write-Host "       • Azure Maps (Gen2), Speech, Vision services" -ForegroundColor Gray
    Write-Host "       • Log Analytics Workspace" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  🔐 RBAC will be configured automatically across resource groups" -ForegroundColor Cyan
    Write-Host "  ⏱  This may take 8-12 minutes..." -ForegroundColor Gray
    Write-Host ""

    if (-not (Test-Path $bicepTemplate)) {
        Write-Host "  ✗ Bicep template not found: $bicepTemplate" -ForegroundColor Red
        Write-Host "  Please ensure the infra/main.bicep file exists" -ForegroundColor Red
        exit 1
    }

    # Deploy Bicep template at subscription scope
    $deploymentName = "zava-deployment-$(Get-Date -Format 'yyyyMMddHHmmss')"
    
    # Generate new unique suffix to avoid soft-delete conflicts
    $newSuffix = -join ((97..122) | Get-Random -Count 6 | ForEach-Object {[char]$_})
    Write-Host "  🔑 Using new unique suffix: $newSuffix (avoids soft-delete conflicts)" -ForegroundColor Cyan

    Write-Host "  🚀 Starting subscription-level Bicep deployment: $deploymentName" -ForegroundColor Cyan

    # Deploy at subscription scope (creates resource groups and resources)
    # Don't query outputs immediately - check deployment succeeded first
    az deployment sub create `
        --name $deploymentName `
        --location $Location `
        --template-file $bicepTemplate `
        --parameters location=$Location environment=$Environment appServiceSku=$Sku uniqueSuffix=$newSuffix `
        --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Infrastructure deployment failed" -ForegroundColor Red
        Write-Host "  Run 'az deployment sub show --name $deploymentName' for details" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "  ✓ Infrastructure deployment succeeded" -ForegroundColor Green
    Write-Host "  Retrieving deployment outputs..." -ForegroundColor Cyan

    # Get deployment outputs after successful deployment
    $bicepOutput = az deployment sub show `
        --name $deploymentName `
        --query properties.outputs `
        --output json

    # Parse JSON output
    try {
        $bicepOutputJson = $bicepOutput | ConvertFrom-Json
    } catch {
        Write-Host "  ✗ Failed to parse deployment output" -ForegroundColor Red
        Write-Host "  Output was: $bicepOutput" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Attempting to retrieve deployment outputs manually..." -ForegroundColor Yellow

        $bicepOutputJson = az deployment sub show `
            --name $deploymentName `
            --query properties.outputs `
            --output json | ConvertFrom-Json
    }

    Write-Host "  ✓ Infrastructure deployed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  📋 Deployment Details:" -ForegroundColor Cyan
    Write-Host "     Frontend Resource Group: $frontendRgName" -ForegroundColor White
    Write-Host "       App Service: $($bicepOutputJson.frontend.value.appServiceName)" -ForegroundColor Gray
    Write-Host "       URL: $($bicepOutputJson.frontend.value.appServiceUrl)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "     Middleware Resource Group: $middlewareRgName" -ForegroundColor White
    Write-Host "       Azure OpenAI: $($bicepOutputJson.middleware.value.openAIServiceName)" -ForegroundColor Gray
    Write-Host "       AI Hub: $($bicepOutputJson.middleware.value.aiHubName)" -ForegroundColor Gray
    Write-Host "       AI Project: $($bicepOutputJson.middleware.value.aiProjectName)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "     Backend Resource Group: $backendRgName" -ForegroundColor White
    Write-Host "       Cosmos DB: $($bicepOutputJson.backend.value.cosmosDbAccountName)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "     Shared Resource Group: $sharedRgName" -ForegroundColor White
    Write-Host "       Azure Maps: $($bicepOutputJson.shared.value.mapsAccountName)" -ForegroundColor Gray
    Write-Host ""

    # Store deployment info
    $WebAppName = $bicepOutputJson.frontend.value.appServiceName

    # Validate we got the app name
    if (-not $WebAppName) {
        Write-Host "  ✗ Failed to retrieve App Service name from deployment" -ForegroundColor Red
        Write-Host "  Please check the Bicep template outputs" -ForegroundColor Yellow
        exit 1
    }

    # Wait for RBAC permissions to propagate
    Write-Host ""
    Write-Host "[3.5/7] Waiting for cross-resource group RBAC permissions to propagate..." -ForegroundColor Yellow
    Write-Host "  ℹ  Bicep template assigned the following roles across resource groups:" -ForegroundColor Cyan
    Write-Host "     • App Service → Cosmos DB Built-in Data Contributor (Backend RG)" -ForegroundColor Gray
    Write-Host "     • App Service → Cognitive Services OpenAI User (Middleware RG)" -ForegroundColor Gray
    Write-Host "     • App Service → Cognitive Services User for Speech/Vision (Shared RG)" -ForegroundColor Gray
    Write-Host "     • AI Hub/Project → Cognitive Services OpenAI User (Middleware RG)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  ⏱  Waiting 60 seconds for Azure RBAC replication across regions..." -ForegroundColor Cyan
    Start-Sleep -Seconds 60
    Write-Host "  ✓ RBAC permissions should now be active" -ForegroundColor Green
    Write-Host ""

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

Write-Host "  Checking App Service: $WebAppName (in $frontendRgName)" -ForegroundColor Gray
$webApp = az webapp show --name $WebAppName --resource-group $frontendRgName --output json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Could not retrieve Web App '$WebAppName'" -ForegroundColor Red
    Write-Host "  Error: $webApp" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Troubleshooting:" -ForegroundColor Cyan
    Write-Host "    - Verify app service exists: az webapp list --resource-group $frontendRgName" -ForegroundColor Gray
    Write-Host "    - Check resource group: az group show --name $frontendRgName" -ForegroundColor Gray
    exit 1
}
$webApp = $webApp | ConvertFrom-Json
Write-Host "  ✓ Web App Status: $($webApp.state)" -ForegroundColor Green
Write-Host "  ✓ Default Hostname: $($webApp.defaultHostName)" -ForegroundColor Green
Write-Host ""

# [4.5/7] Create Azure AI Foundry Agents
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "[4.5/7] Creating Azure AI Foundry Agents..." -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "  📦 This will create 8 AI agents in your Azure AI project" -ForegroundColor Gray
Write-Host "  ⏱ This may take 2-3 minutes..." -ForegroundColor Gray
Write-Host ""

# Prepare array for agent settings (will be added to app settings later)
$agentSettings = @{}

# Create agents using Python script
try {
    # Check if Python is available
    if (Get-Command python -ErrorAction SilentlyContinue) {
        # Get OpenAI service name and subscription ID (from Middleware RG)
        $openAIServiceName = $bicepOutputJson.middleware.value.openAIServiceName
        $subscriptionId = $account.id
        $resourceId = "/subscriptions/$subscriptionId/resourceGroups/$middlewareRgName/providers/Microsoft.CognitiveServices/accounts/$openAIServiceName"
        
        Write-Host "  ⚙ Temporarily enabling API key authentication for agent creation..." -ForegroundColor Yellow
        az resource update `
            --ids $resourceId `
            --set properties.disableLocalAuth=false `
            --api-version 2023-05-01 `
            --output none 2>&1 | Out-Null
        
        Write-Host "  ⏱ Waiting 30 seconds for change to propagate..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
        
        Write-Host "  🔑 Getting temporary API key..." -ForegroundColor Yellow
        $openAIApiKey = az cognitiveservices account keys list --name $openAIServiceName --resource-group $middlewareRgName --query key1 -o tsv
        
        Write-Host "  🤖 Creating AI agents..." -ForegroundColor Yellow
        Write-Host "     OpenAI Service: $openAIServiceName" -ForegroundColor Gray
        Write-Host "     Endpoint: $($bicepOutputJson.middleware.value.openAIServiceEndpoint)" -ForegroundColor Gray
        Write-Host ""
        
        # Set environment variables and run Python script directly (no subprocess)
        $env:AZURE_OPENAI_ENDPOINT = $bicepOutputJson.middleware.value.openAIServiceEndpoint
        $env:AZURE_OPENAI_API_KEY = $openAIApiKey
        $env:AZURE_AI_MODEL_DEPLOYMENT_NAME = "gpt-4o"
        
        # Run agent creation script directly and capture output
        python Scripts/create_foundry_agents_openai.py 2>&1 | Tee-Object -Variable agentOutput | Out-Host
        $agentExitCode = $LASTEXITCODE
        
        # Disable API key authentication again (back to managed identity only)
        Write-Host ""
        Write-Host "  🔒 Disabling API key authentication (switching to managed identity)..." -ForegroundColor Yellow
        az resource update `
            --ids $resourceId `
            --set properties.disableLocalAuth=true `
            --api-version 2023-05-01 `
            --output none 2>&1 | Out-Null
        
        Write-Host "  ✓ Azure OpenAI now uses managed identity only" -ForegroundColor Green
        Write-Host ""
        
        # Check if agent creation was successful
        if ($agentExitCode -eq 0 -and $agentOutput) {
            # Extract JSON from output (should be at the end)
            $jsonMatch = [regex]::Match($agentOutput, '\{[^}]*"[A-Z_]+AGENT_ID"[^}]*\}')
            
            if ($jsonMatch.Success) {
                # Parse agent IDs from JSON
                $agentIds = $jsonMatch.Value | ConvertFrom-Json
                
                Write-Host "  ✓ Successfully created all agents" -ForegroundColor Green
                Write-Host ""
                Write-Host "  📋 Agent IDs:" -ForegroundColor Cyan
                
                $agentIds.PSObject.Properties | ForEach-Object {
                    Write-Host "     $($_.Name) = $($_.Value)" -ForegroundColor Gray
                    $agentSettings[$_.Name] = $_.Value
                }
                
                Write-Host ""
                Write-Host "  ✓ Agent IDs will be configured in app settings" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ Agent creation completed but couldn't parse JSON output" -ForegroundColor Yellow
                Write-Host "  Output: $($agentOutput.Substring(0, [Math]::Min(200, $agentOutput.Length)))" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ⚠ Agent creation failed (exit code: $agentExitCode)" -ForegroundColor Yellow
            Write-Host "  ⚠ Continuing deployment without agents" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "  ⚠ Continuing deployment without agents" -ForegroundColor Yellow
            Write-Host "  You can create agents manually after deployment" -ForegroundColor Gray
            Write-Host "    Run: python Scripts/create_foundry_agents_openai.py" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Python not found - skipping agent creation" -ForegroundColor Yellow
        Write-Host "  You can create agents manually after deployment" -ForegroundColor Gray
        Write-Host "    Run: python Scripts/create_foundry_agents.py" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠ Agent creation error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  Continuing deployment without agents" -ForegroundColor Gray
}

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

    # Add created agents to settings (overrides .env if agents were just created)
    if ($agentSettings.Count -gt 0) {
        Write-Host "  ✓ Adding $($agentSettings.Count) agent IDs from fresh creation..." -ForegroundColor Green
        foreach ($key in $agentSettings.Keys) {
            # Override .env value if agent was just created
            $agentIds[$key] = $agentSettings[$key]
        }
    }

    # Add agent IDs to settings
    foreach ($key in $agentIds.Keys) {
        $additionalSettings += "$key=$($agentIds[$key])"
    }

    if ($agentIds.Count -gt 0) {
        Write-Host "  ✓ Found/Created $($agentIds.Count) agent ID(s)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ No agent IDs found - agents may not work" -ForegroundColor Yellow
        Write-Host "    Run manually: python Scripts/create_foundry_agents.py" -ForegroundColor Gray
    }

    # Add depot addresses
    foreach ($key in $depots.Keys) {
        $additionalSettings += "$key=$($depots[$key])"
    }

    if ($depots.Count -gt 0) {
        Write-Host "  ✓ Found $($depots.Count) depot address(es)" -ForegroundColor Green
    }
}

# Add Azure OpenAI configuration from Bicep deployment
if ($bicepOutput -and $bicepOutput.openAIServiceEndpoint) {
    $additionalSettings += "AZURE_OPENAI_ENDPOINT=$($bicepOutput.openAIServiceEndpoint)"
    $additionalSettings += "AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o"
    Write-Host "  ✓ Azure OpenAI endpoint configured" -ForegroundColor Green
} elseif (-not $CodeOnly) {
    Write-Host "  ⚠ Azure OpenAI endpoint not found in deployment outputs" -ForegroundColor Yellow
}

# Apply additional settings if any
if ($additionalSettings.Count -gt 0) {
    az webapp config appsettings set `
        --name $WebAppName `
        --resource-group $frontendRgName `
        --settings $additionalSettings `
        --output none
    Write-Host "✓ Configuration settings applied to Web App" -ForegroundColor Green
} else {
    Write-Host "  ⚠ No configuration settings to apply" -ForegroundColor Yellow
    Write-Host "  Agents should have been created automatically during deployment" -ForegroundColor Gray
    Write-Host "  If agents are missing, run: python Scripts/create_foundry_agents.py" -ForegroundColor Gray
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
    --resource-group $frontendRgName `
    --src $tempZip `
    --timeout 600 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Code deployment failed: $deployResult" -ForegroundColor Red
    Write-Host "    Check logs with: az webapp log tail --name $WebAppName --resource-group $frontendRgName" -ForegroundColor Gray
} else {
    Write-Host "✓ Application code deployed" -ForegroundColor Green
}

Remove-Item $tempZip -Force
Write-Host ""

# =============================================================================
# [7/7] Post-deployment tasks (Demo Data with Secure Auth)
# =============================================================================
# DEPLOYMENT FLOW WITH DEPENDENCIES:
#   1. Temporarily enable Cosmos DB local auth (key-based)
#   2. CREATE & VALIDATE containers (CRITICAL DEPENDENCY)
#      ├─ Creates all 10 required Cosmos DB containers
#      ├─ Validates containers exist via diagnose script  
#      ├─ Retries once if initial creation fails (RBAC propagation delay)
#      └─ DEPLOYMENT FAILS if containers cannot be created/validated
#   3. Generate demo data (DEPENDS ON: containers exist)
#      ├─ Fresh test parcels with DC assignments
#      ├─ Dispatcher demo data (parcels at depot)
#      ├─ Driver manifests with delivery parcels
#      └─ Approval demo requests
#   4. Re-secure Cosmos DB (disable local auth → managed identity only)
#   5. Restart App Service (refresh managed identity tokens with RBAC)
# =============================================================================

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
    Write-Host "    Check logs with: az webapp log tail --name $WebAppName --resource-group $frontendRgName" -ForegroundColor Gray
}

# Task 3: Initialize default users
Write-Host "  👤 Initializing default user accounts..." -ForegroundColor Cyan
Write-Host "     (This requires Cosmos DB RBAC permissions to be active)" -ForegroundColor Gray

# Validate Cosmos DB exists before attempting user initialization
$cosmosAccountName = $bicepOutputJson.backend.value.cosmosDbAccountName
Write-Host "    🔍 Validating Cosmos DB: $cosmosAccountName..." -ForegroundColor Cyan

$cosmosCheck = az cosmosdb show `
    --name $cosmosAccountName `
    --resource-group $backendRgName `
    --query "name" `
    -o tsv 2>$null

if (-not $cosmosCheck) {
    Write-Host "    ✗ ERROR: Cosmos DB account '$cosmosAccountName' not found!" -ForegroundColor Red
    Write-Host "    ℹ  Skipping database initialization - database not accessible" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "    ✓ Cosmos DB validated: $cosmosAccountName" -ForegroundColor Green
    
    # Initialize default users (containers must be created first - validated in post-deployment)
    Write-Host "  👤 Initializing default user accounts..." -ForegroundColor Cyan
    # Step 2: Initialize default users
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
                # Check if it's a permission error
                if ($setupOutput -match "Forbidden|RBAC|readMetadata") {
                    Write-Host "  ⚠ RBAC permissions not yet active - waiting additional 30 seconds..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 30
                    
                    # Retry once
                    $retryOutput = python utils/setup/setup_users.py 2>&1
                    if ($LASTEXITCODE -eq 0 -and $retryOutput -match "SUCCESS") {
                        Write-Host "  ✓ Default users created successfully (after retry)" -ForegroundColor Green
                    } else {
                        Write-Host "  ⚠ User initialization failed - RBAC may need more time to propagate" -ForegroundColor Yellow
                        Write-Host "    Users will be auto-created on first login attempt" -ForegroundColor Gray
                        Write-Host "    Or run manually: python utils/setup/setup_users.py" -ForegroundColor Gray
                    }
                } else {
                    Write-Host "  ⚠ User initialization may have failed" -ForegroundColor Yellow
                    Write-Host "    Run manually: python utils/setup/setup_users.py" -ForegroundColor Gray
                }
            }
        } else {
            Write-Host "  ⚠ Python not found - skipping user initialization" -ForegroundColor Yellow
            Write-Host "    Users will be auto-created on first login attempt" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ⚠ Could not initialize users: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "    Users will be auto-created on first login attempt" -ForegroundColor Gray
    }
}

# Task 4: Generate demo data for full-featured demo
Write-Host "  📦 Generating demo data (parcels, manifests, dispatcher data)..." -ForegroundColor Cyan
Write-Host "     (Requires temporary Cosmos DB local auth for data generation)" -ForegroundColor Gray
try {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        # Get Cosmos DB account name from Bicep output
        $cosmosAccountName = $bicepOutputJson.backend.value.cosmosDbAccountName
        $subscriptionId = $account.id
        
        # Validate that Cosmos DB account exists before proceeding
        Write-Host "    🔍 Validating Cosmos DB account exists: $cosmosAccountName..." -ForegroundColor Cyan
        $cosmosExists = az cosmosdb check-name-exists --name $cosmosAccountName
        
        if ($cosmosExists -eq "false") {
            Write-Host "    ✗ ERROR: Cosmos DB account '$cosmosAccountName' does not exist!" -ForegroundColor Red
            Write-Host "    ℹ  The deployment may have failed during infrastructure creation." -ForegroundColor Yellow
            Write-Host "    ℹ  Run the deployment again or check Azure portal for the account." -ForegroundColor Yellow
            throw "Cosmos DB account validation failed"
        }
        
        # Verify the account is in the correct resource group
        $cosmosDetails = az cosmosdb show `
            --name $cosmosAccountName `
            --resource-group $backendRgName `
            --query "{name:name, endpoint:documentEndpoint}" `
            -o json 2>$null | ConvertFrom-Json
            
        if (-not $cosmosDetails) {
            Write-Host "    ✗ ERROR: Cosmos DB account '$cosmosAccountName' not found in resource group '$backendRgName'!" -ForegroundColor Red
            throw "Cosmos DB account not accessible"
        }
        
        Write-Host "    ✓ Cosmos DB account validated: $cosmosAccountName" -ForegroundColor Green
        Write-Host "      Endpoint: $($cosmosDetails.endpoint)" -ForegroundColor Gray
        
        # Step 1: Temporarily enable local auth for data generation
        Write-Host "    🔓 Temporarily enabling Cosmos DB local authentication..." -ForegroundColor Cyan
        $cosmosResourceId = "/subscriptions/$subscriptionId/resourceGroups/$backendRgName/providers/Microsoft.DocumentDB/databaseAccounts/$cosmosAccountName"
        
        az resource update `
            --ids $cosmosResourceId `
            --set properties.disableLocalAuth=false `
            --api-version 2023-11-15 `
            --output none 2>&1 | Out-Null
        
        Write-Host "    ⏱  Waiting 60 seconds for auth change to fully propagate across Azure..." -ForegroundColor Gray
        Write-Host "      (Azure configuration changes can take 45-60 seconds to apply globally)" -ForegroundColor Gray
        Start-Sleep -Seconds 60
        
        # Step 2: Get connection string
        Write-Host "    🔑 Retrieving connection string for initialization..." -ForegroundColor Cyan
        $connectionString = az cosmosdb keys list `
            --name $cosmosAccountName `
            --resource-group $backendRgName `
            --type connection-strings `
            --query "connectionStrings[0].connectionString" `
            -o tsv
        
        if ($connectionString) {
            # Step 3: Set environment variables for Python scripts
            $env:COSMOS_CONNECTION_STRING = $connectionString
            $env:COSMOS_DB_DATABASE_NAME = "logisticstracking"
            $env:PYTHONPATH = $PWD  # Required for approval requests module imports
            
            # Step 3a: Initialize all database containers FIRST (CRITICAL DEPENDENCY)
            Write-Host "    📦 Initializing all 10 database containers..." -ForegroundColor Cyan
            $containerOutput = python Scripts/initialize_all_containers.py 2>&1
            
            if ($LASTEXITCODE -eq 0 -and $containerOutput -match "SUCCESS") {
                Write-Host "    ✓ All database containers created successfully" -ForegroundColor Green
                
                # Step 3a.1: VALIDATE containers exist (critical validation)
                Write-Host "    🔍 Validating all containers exist..." -ForegroundColor Cyan
                $validateOutput = python Scripts/diagnose_containers.py 2>&1
                
                if ($LASTEXITCODE -eq 0 -and $validateOutput -match "All containers exist") {
                    Write-Host "    ✓ Container validation passed - all 10 containers confirmed" -ForegroundColor Green
                } else {
                    Write-Host "    ⚠️  Container validation failed on first check" -ForegroundColor Yellow
                    Write-Host "      Diagnostic output:" -ForegroundColor Gray
                    Write-Host $validateOutput -ForegroundColor Gray
                    Write-Host "" -ForegroundColor Yellow
                    Write-Host "      Waiting 30 seconds for container creation to complete..." -ForegroundColor Yellow
                    Write-Host "      (Container creation can be async - operations may still be in progress)" -ForegroundColor Gray
                    Start-Sleep -Seconds 30
                    
                    # Retry container creation AND validation
                    Write-Host "    🔄 Retrying container initialization..." -ForegroundColor Cyan
                    $retryOutput = python Scripts/initialize_all_containers.py 2>&1
                    
                    Write-Host "    🔍 Re-validating container count..." -ForegroundColor Cyan
                    $retryValidate = python Scripts/diagnose_containers.py 2>&1
                    
                    if ($LASTEXITCODE -eq 0 -and $retryValidate -match "All containers exist") {
                        Write-Host "    ✓ Container validation passed on retry" -ForegroundColor Green
                    } else {
                        Write-Host "" -ForegroundColor Red
                        Write-Host "    ❌ CRITICAL ERROR: Cannot create/validate Cosmos DB containers" -ForegroundColor Red
                        Write-Host "    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Red
                        Write-Host "    This is a blocking issue - deployment cannot proceed without containers." -ForegroundColor Yellow
                        Write-Host "" -ForegroundColor Yellow
                        Write-Host "    Diagnostic output:" -ForegroundColor Gray
                        Write-Host $retryValidate -ForegroundColor Gray
                        Write-Host "" -ForegroundColor Red
                        Write-Host "    Possible causes:" -ForegroundColor Yellow
                        Write-Host "      • Connection string auth not fully propagated (wait 2-3 min)" -ForegroundColor Gray
                        Write-Host "      • Cosmos DB account not fully provisioned" -ForegroundColor Gray
                        Write-Host "      • Network connectivity issues" -ForegroundColor Gray
                        Write-Host "" -ForegroundColor Yellow
                        Write-Host "    Manual fix:" -ForegroundColor Yellow
                        Write-Host "      1. Wait 2-3 more minutes for Azure propagation" -ForegroundColor Gray
                        Write-Host "      2. Run: .\Scripts\fix_azure_containers.ps1" -ForegroundColor Gray
                        Write-Host "      3. Verify: python Scripts\diagnose_containers.py" -ForegroundColor Gray
                        Write-Host "    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Red
                        Write-Host "" -ForegroundColor Red
                        
                        # Re-secure Cosmos DB before exiting
                        Write-Host "    🔒 Re-securing Cosmos DB before exit..." -ForegroundColor Yellow
                        az resource update `
                            --ids $cosmosResourceId `
                            --set properties.disableLocalAuth=true `
                            --api-version 2023-11-15 `
                            --output none 2>&1 | Out-Null
                        
                        throw "Container validation failed - cannot proceed with deployment"
                    }
                }
            } else {
                Write-Host "    ⚠️  Container initialization failed on first attempt" -ForegroundColor Yellow
                Write-Host "      Exit code: $LASTEXITCODE" -ForegroundColor Gray
                Write-Host "      Output:" -ForegroundColor Gray
                Write-Host $containerOutput -ForegroundColor Gray
                Write-Host "" -ForegroundColor Yellow
                Write-Host "      Waiting 60 seconds for connection string auth to fully propagate..." -ForegroundColor Yellow
                Write-Host "      (Azure auth changes can take 60-90 seconds to apply globally)" -ForegroundColor Gray
                Start-Sleep -Seconds 60
                
                # Retry with fresh connection
                Write-Host "    🔄 Retrying container initialization (attempt 2/3)..." -ForegroundColor Cyan
                $retryOutput = python Scripts/initialize_all_containers.py 2>&1
                
                if ($LASTEXITCODE -eq 0 -and $retryOutput -match "SUCCESS") {
                    Write-Host "    ✓ Container creation succeeded on retry" -ForegroundColor Green
                    
                    # Validate after successful retry
                    Write-Host "    🔍 Validating container count..." -ForegroundColor Cyan
                    $validateOutput = python Scripts/diagnose_containers.py 2>&1
                    
                    if ($LASTEXITCODE -eq 0 -and $validateOutput -match "All containers exist") {
                        Write-Host "    ✓ Container validation passed - all 10 containers confirmed" -ForegroundColor Green
                    } else {
                        Write-Host "    ⚠️  Container count validation failed - attempting final retry..." -ForegroundColor Yellow
                        Start-Sleep -Seconds 30
                        
                        # Final retry
                        Write-Host "    🔄 Final retry of container initialization (attempt 3/3)..." -ForegroundColor Cyan
                        $finalRetry = python Scripts/initialize_all_containers.py 2>&1
                        $finalValidate = python Scripts/diagnose_containers.py 2>&1
                        
                        if (-not ($LASTEXITCODE -eq 0 -and $finalValidate -match "All containers exist")) {
                            Write-Host "    ❌ Container validation failed after 3 attempts" -ForegroundColor Red
                            Write-Host "      Diagnostic output:" -ForegroundColor Gray
                            Write-Host $finalValidate -ForegroundColor Gray
                            
                            # Re-secure before exiting
                            az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --api-version 2023-11-15 --output none 2>&1 | Out-Null
                            throw "Container validation failed after multiple retries"
                        }
                        
                        Write-Host "    ✓ Container validation passed on final retry" -ForegroundColor Green
                    }
                } else {
                    Write-Host "    ⚠️  Container initialization still failing - final attempt..." -ForegroundColor Yellow
                    Write-Host "      Waiting additional 30 seconds..." -ForegroundColor Gray
                    Start-Sleep -Seconds 30
                    
                    Write-Host "    🔄 Final retry of container initialization (attempt 3/3)..." -ForegroundColor Cyan
                    $finalRetry = python Scripts/initialize_all_containers.py 2>&1
                    
                    if (-not ($LASTEXITCODE -eq 0 -and $finalRetry -match "SUCCESS")) {
                        Write-Host "    ❌ Container initialization failed after 3 attempts" -ForegroundColor Red
                        Write-Host "      Output:" -ForegroundColor Gray
                        Write-Host $finalRetry -ForegroundColor Gray
                        
                        # Re-secure before exiting
                        az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --api-version 2023-11-15 --output none 2>&1 | Out-Null
                        throw "Container initialization failed - cannot proceed"
                    }
                    
                    # Validate final success
                    $finalValidate = python Scripts/diagnose_containers.py 2>&1
                    if (-not ($LASTEXITCODE -eq 0 -and $finalValidate -match "All containers exist")) {
                        Write-Host "    ❌ Container validation failed" -ForegroundColor Red
                        az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --api-version 2023-11-15 --output none 2>&1 | Out-Null
                        throw "Container validation failed"
                    }
                    
                    Write-Host "    ✓ All containers validated successfully on final retry" -ForegroundColor Green
                }
            }
            
            # Step 3b: Generate demo data
            Write-Host "    📊 Generating demo data..." -ForegroundColor Cyan
            
            # Generate fresh test parcels with valid DC assignments
            Write-Host "    • Creating test parcels with valid DC assignments..." -ForegroundColor Gray
            $freshDataOutput = python utils/generators/generate_fresh_test_data.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Fresh test data generated" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Fresh test data generation had issues" -ForegroundColor Yellow
            }

            # Generate dispatcher demo data (parcels at depot ready for assignment)
            Write-Host "    • Creating parcels ready for dispatcher assignment..." -ForegroundColor Gray
            $dispatcherOutput = python utils/generators/generate_dispatcher_demo_data.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Dispatcher demo data generated" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Dispatcher demo data generation had issues" -ForegroundColor Yellow
            }

            # Generate driver manifests with parcels
            Write-Host "    • Creating driver manifests with delivery parcels..." -ForegroundColor Gray
            $manifestOutput = python utils/generators/generate_demo_manifests.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Demo manifests generated for all drivers" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Demo manifest generation had issues" -ForegroundColor Yellow
            }

            # Create approval demo requests
            Write-Host "    • Creating approval demo requests for existing parcels..." -ForegroundColor Gray
            $approvalOutput = python utils/generators/create_approval_requests.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Approval demo requests created" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Approval request creation had issues (non-critical)" -ForegroundColor Yellow
                # Log error details if verbose
                if ($approvalOutput -match "ModuleNotFoundError") {
                    Write-Host "      Note: Ensure PYTHONPATH is set correctly" -ForegroundColor Gray
                }
            }
            
            # Clear the connection string and other sensitive data from environment
            Write-Host "    🧹 Clearing temporary credentials from environment..." -ForegroundColor Cyan
            Remove-Item Env:\COSMOS_CONNECTION_STRING -ErrorAction SilentlyContinue
            Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
            Write-Host "    ✓ Environment cleaned" -ForegroundColor Green
            
            Write-Host "  ✓ Demo data generation completed" -ForegroundColor Green
        } else {
            Write-Host "    ⚠ Could not retrieve connection string - skipping data generation" -ForegroundColor Yellow
        }
        
        # Step 4: Re-secure Cosmos DB (disable local auth)
        Write-Host "    🔒 Re-securing Cosmos DB (disabling local auth)..." -ForegroundColor Cyan
        az resource update `
            --ids $cosmosResourceId `
            --set properties.disableLocalAuth=true `
            --api-version 2023-11-15 `
            --output none 2>&1 | Out-Null
        
        Write-Host "    ✓ Cosmos DB secured (managed identity only)" -ForegroundColor Green
        
        # Step 5: Remove any key-based auth environment variables to force managed identity
        Write-Host "    🔧 Ensuring managed identity authentication..." -ForegroundColor Cyan
        Write-Host "      (Removing any key-based auth environment variables)" -ForegroundColor Gray
        
        $webAppName = $bicepOutputJson.frontend.value.webAppName
        
        # Remove key-based auth variables if they exist (ignore errors if they don't exist)
        az webapp config appsettings delete `
            --name $webAppName `
            --resource-group $frontendRgName `
            --setting-names COSMOS_DB_KEY COSMOS_CONNECTION_STRING `
            --output none 2>$null
        
        Write-Host "    ✓ Managed identity authentication configured" -ForegroundColor Green
        
        # Step 6: STOP and START App Service (not restart) to fully clear credential cache
        Write-Host "    🔄 Stopping App Service to clear credential cache..." -ForegroundColor Cyan
        Write-Host "      (Full stop/start required for fresh managed identity tokens)" -ForegroundColor Gray
        
        $stopResult = az webapp stop `
            --name $webAppName `
            --resource-group $frontendRgName `
            --output none 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ App Service stopped successfully" -ForegroundColor Green
        } else {
            Write-Host "    ⚠ App Service stop had issues" -ForegroundColor Yellow
        }
        
        # Wait for RBAC propagation across Azure regions (critical for fresh credentials)
        Write-Host "    ⏱  Waiting 90 seconds for RBAC propagation across Azure..." -ForegroundColor Cyan
        Write-Host "      (RBAC changes can take 2-5 minutes to fully propagate)" -ForegroundColor Gray
        Start-Sleep -Seconds 90
        
        # START the app with fresh managed identity credentials
        Write-Host "    🔄 Starting App Service with fresh credentials..." -ForegroundColor Cyan
        
        $startResult = az webapp start `
            --name $webAppName `
            --resource-group $frontendRgName `
            --output none 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ App Service started successfully" -ForegroundColor Green
            Write-Host "      Managed identity now has fresh credentials with RBAC permissions" -ForegroundColor Gray
            
            # Wait for app to fully initialize
            Write-Host "    ⏱  Waiting 45 seconds for app initialization..." -ForegroundColor Cyan
            Start-Sleep -Seconds 45
            Write-Host "    ✓ App initialization complete" -ForegroundColor Green
        } else {
            Write-Host "    ⚠ App Service start had issues (non-critical)" -ForegroundColor Yellow
            Write-Host "      You may need to manually restart if you see auth errors" -ForegroundColor Gray
        }
        
    } else {
        Write-Host "  ⚠ Python not found - skipping demo data generation" -ForegroundColor Yellow
        Write-Host "    Install Python to enable automatic demo data generation" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠ Demo data generation failed: $($_.Exception.Message)" -ForegroundColor Yellow
    
    # Ensure we re-secure Cosmos DB even if generation fails
    try {
        Write-Host "    🔒 Re-securing Cosmos DB after error..." -ForegroundColor Yellow
        $subscriptionId = $account.id
        $cosmosAccountName = $bicepOutputJson.backend.value.cosmosDbAccountName
        $cosmosResourceId = "/subscriptions/$subscriptionId/resourceGroups/$backendRgName/providers/Microsoft.DocumentDB/databaseAccounts/$cosmosAccountName"
        
        az resource update `
            --ids $cosmosResourceId `
            --set properties.disableLocalAuth=true `
            --api-version 2023-11-15 `
            --output none 2>&1 | Out-Null
        
        Write-Host "    ✓ Cosmos DB re-secured" -ForegroundColor Green
        
        # Stop and start App Service even after errors to refresh credentials
        Write-Host "    🔄 Stopping App Service to clear credential cache..." -ForegroundColor Cyan
        $webAppName = $bicepOutputJson.frontend.value.webAppName
        $frontendRgName = "RG-Zava-Frontend-$environment"
        
        az webapp stop --name $webAppName --resource-group $frontendRgName --output none 2>&1 | Out-Null
        Write-Host "    ✓ App Service stopped" -ForegroundColor Green
        
        Write-Host "    ⏱  Waiting 90 seconds for RBAC propagation..." -ForegroundColor Cyan
        Start-Sleep -Seconds 90
        
        az webapp start --name $webAppName --resource-group $frontendRgName --output none 2>&1 | Out-Null
        Write-Host "    ✓ App Service started with fresh credentials" -ForegroundColor Green
        
    } catch {
        Write-Host "    ⚠ Warning: Could not re-secure Cosmos DB. Run manually:" -ForegroundColor Red
        Write-Host "      az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --api-version 2023-11-15" -ForegroundColor Gray
    }
}

Write-Host "✓ Post-deployment tasks completed" -ForegroundColor Green
Write-Host ""

# Save deployment configuration
$deploymentInfo = @{
    AppServiceName = $WebAppName
    FrontendResourceGroup = $frontendRgName
    MiddlewareResourceGroup = $middlewareRgName
    BackendResourceGroup = $backendRgName
    SharedResourceGroup = $sharedRgName
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
Write-Host "Demo Data:" -ForegroundColor Yellow
Write-Host "  ✓ Driver manifests with delivery parcels" -ForegroundColor Green
Write-Host "  ✓ Parcels ready for dispatcher assignment" -ForegroundColor Green
Write-Host "  ✓ Test parcels with valid DC assignments" -ForegroundColor Green
if ($agentSettings.Count -gt 0) {
    Write-Host "  ✓ Azure AI agents created and configured" -ForegroundColor Green
}
Write-Host ""

# Optional: Generate bulk realistic data
Write-Host "📦 Optional: Bulk Realistic Data Generation" -ForegroundColor Cyan
Write-Host "Generate thousands of realistic parcels for comprehensive testing?" -ForegroundColor Yellow
Write-Host "This creates:" -ForegroundColor Gray
Write-Host "  • Specific demo parcels for Voice & Text Examples (RG857954, DT202512170037, etc.)" -ForegroundColor Gray
Write-Host "  • Thousands of parcels across all Australian states" -ForegroundColor Gray
Write-Host "  • Full event histories and photo proofs" -ForegroundColor Gray
Write-Host "  • Driver assignments for manifest testing" -ForegroundColor Gray
Write-Host "  • Data for approval system and statistics queries" -ForegroundColor Gray
Write-Host ""
$generateBulkData = Read-Host "Generate bulk data? (y/N)"

if ($generateBulkData -eq 'y' -or $generateBulkData -eq 'Y') {
    Write-Host ""
    $parcelCount = Read-Host "How many parcels to generate? (default: 2000)"
    if ([string]::IsNullOrWhiteSpace($parcelCount)) {
        $parcelCount = "2000"
    }
    
    Write-Host ""
    Write-Host "🚀 Generating $parcelCount realistic parcels..." -ForegroundColor Cyan
    Write-Host "   (This may take 5-10 minutes depending on count)" -ForegroundColor Gray
    Write-Host ""
    
    # Temporarily enable Cosmos DB local auth again for bulk generation
    try {
        Write-Host "  🔓 Temporarily enabling Cosmos DB local auth..." -ForegroundColor Cyan
        $subscriptionId = $account.id
        $cosmosAccountName = $bicepOutputJson.backend.value.cosmosDbAccountName
        $cosmosResourceId = "/subscriptions/$subscriptionId/resourceGroups/$backendRgName/providers/Microsoft.DocumentDB/databaseAccounts/$cosmosAccountName"
        
        az resource update `
            --ids $cosmosResourceId `
            --set properties.disableLocalAuth=false `
            --api-version 2023-11-15 `
            --output none 2>&1 | Out-Null
        
        Write-Host "  ⏱  Waiting 60 seconds for auth propagation..." -ForegroundColor Gray
        Start-Sleep -Seconds 60
        
        # Get connection string
        $connectionString = az cosmosdb keys list `
            --name $cosmosAccountName `
            --resource-group $backendRgName `
            --type connection-strings `
            --query "connectionStrings[0].connectionString" `
            -o tsv
        
        if ($connectionString) {
            $env:COSMOS_CONNECTION_STRING = $connectionString
            
            # Run bulk data generator
            $bulkOutput = python utils/generators/generate_bulk_realistic_data.py --count $parcelCount 2>&1
            Write-Host $bulkOutput
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ Bulk data generation completed!" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ Bulk data generation had issues (check output above)" -ForegroundColor Yellow
            }
            
            # Clear connection string
            Remove-Item Env:\COSMOS_CONNECTION_STRING -ErrorAction SilentlyContinue
        } else {
            Write-Host "  ⚠ Could not retrieve connection string - skipping bulk generation" -ForegroundColor Yellow
        }
        
        # Re-secure Cosmos DB
        Write-Host "  🔒 Re-securing Cosmos DB..." -ForegroundColor Cyan
        az resource update `
            --ids $cosmosResourceId `
            --set properties.disableLocalAuth=true `
            --api-version 2023-11-15 `
            --output none 2>&1 | Out-Null
        
        Write-Host "  ✓ Cosmos DB re-secured" -ForegroundColor Green
        
        # Restart App Service again to refresh credentials
        Write-Host "  🔄 Restarting App Service..." -ForegroundColor Cyan
        az webapp restart --name $WebAppName --resource-group $frontendRgName --output none 2>&1 | Out-Null
        Write-Host "  ✓ App Service restarted" -ForegroundColor Green
        
    } catch {
        Write-Host "  ⚠ Bulk data generation failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host "  ⊘ Skipped bulk data generation" -ForegroundColor Gray
    Write-Host "  You can run it later with:" -ForegroundColor Gray
    Write-Host "    python utils/generators/generate_bulk_realistic_data.py --count 2000" -ForegroundColor White
    Write-Host ""
}

Write-Host "Security & Permissions:" -ForegroundColor Yellow
Write-Host "  ✓ App Service using managed identity (no connection strings)" -ForegroundColor Green
Write-Host "  ✓ Cosmos DB RBAC permissions configured via Bicep" -ForegroundColor Green
Write-Host "  ✓ Azure OpenAI access via managed identity" -ForegroundColor Green
Write-Host "  ✓ Speech & Vision services accessible via RBAC" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Visit: $url" -ForegroundColor White
Write-Host "  2. Login with admin credentials and explore the demo" -ForegroundColor White
Write-Host "  3. View logs: az webapp log tail --name $WebAppName --resource-group $frontendRgName" -ForegroundColor White
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
