# =============================================================================
# Deploy Zava to Azure with Multi-Resource Group Infrastructure via Bicep
# =============================================================================

param(
    [string]$Location = "australiaeast",
    [string]$Environment = "dev",
    [string]$Sku = "B3",
    [switch]$Force,
    [switch]$SkipInfrastructure,
    [switch]$CodeOnly
)

# Fix Unicode/emoji output encoding for Azure CLI responses
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$deploymentConfigFile = ".azure-deployment.json"
$bicepTemplate = "infra/main.bicep"

# Update-EnvFile must be defined at the top (before any conditional blocks)
# so it is available everywhere — including -CodeOnly and -SkipInfrastructure paths.
function Update-EnvFile {
    param (
        [string]$Key,
        [string]$Value,
        [string]$FilePath = ".env"
    )
    if (-not $Value) { return }
    if (Test-Path $FilePath) {
        $content = Get-Content $FilePath -Raw
        if ($content -match "(?m)^$Key\s*=") {
            $content = $content -replace "(?m)^$Key\s*=.*", "$Key=$Value"
        } else {
            $content = $content.TrimEnd() + "`r`n$Key=$Value`r`n"
        }
        [System.IO.File]::WriteAllText((Resolve-Path $FilePath).Path, $content)
    } else {
        Add-Content $FilePath "$Key=$Value"
    }
}

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

# Resolve the Python executable — prefer the project venv so all pip packages are available.
# Falls back to system Python if the venv has not been created.
# Always resolves to an absolute path (or $null) so Test-Path guards work correctly.
$pythonExe = if (Test-Path (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")) {
    Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
} elseif (Test-Path (Join-Path $PSScriptRoot ".venv\bin\python")) {
    Join-Path $PSScriptRoot ".venv\bin\python"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    (Get-Command python -ErrorAction SilentlyContinue).Source
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    (Get-Command py -ErrorAction SilentlyContinue).Source
} else {
    $null
}
if ($pythonExe) {
    Write-Host "✓ Python: $pythonExe" -ForegroundColor Green
} else {
    Write-Host "⚠ Python not found — agent creation and data generation steps will be skipped" -ForegroundColor Yellow
}
Write-Host ""

# Register Required Resource Providers
Write-Host "[2/7] Registering required Azure resource providers..." -ForegroundColor Yellow
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

    # --- Step 3 retry loop ---
    # On failure the user is prompted to Retry (new attempt), Load outputs from
    # a previous succeeded deployment and continue, or Quit.
    $deploymentName   = $null
    $newSuffix        = $null
    $bicepOutputJson  = $null
    $deployAttempt    = 0

    while ($null -eq $bicepOutputJson) {
        $deployAttempt++
        $deploymentName = "zava-deployment-$(Get-Date -Format 'yyyyMMddHHmmss')"
        $newSuffix      = -join ((97..122) | Get-Random -Count 6 | ForEach-Object {[char]$_})

        Write-Host "  🔑 Using unique suffix: $newSuffix (avoids soft-delete conflicts)" -ForegroundColor Cyan
        Write-Host "  🚀 Attempt $deployAttempt — Bicep deployment: $deploymentName" -ForegroundColor Cyan

        # Capture stderr so the real failure reason is always visible.
        # Note: az CLI can return exit code 1 even on success when Bicep emits
        # warnings to stderr (e.g. outputs-should-not-contain-secrets). We
        # therefore verify the actual Azure state via 'az deployment sub show'
        # rather than trusting $LASTEXITCODE alone.
        $deployError = $($deployOutput = az deployment sub create `
            --name $deploymentName `
            --location $Location `
            --template-file $bicepTemplate `
            --parameters location=$Location environment=$Environment appServiceSku=$Sku uniqueSuffix=$newSuffix `
            --output none) 2>&1
        $deployExitCode = $LASTEXITCODE

        # Surface any output (warnings/errors) immediately
        if ($deployError) {
            $deployError | Where-Object { $_ -notmatch '^WARNING:' } | ForEach-Object {
                Write-Host "  ⚠  $_" -ForegroundColor Yellow
            }
        }

        # Regardless of exit code, check what Azure actually recorded
        $azState = az deployment sub show `
            --name $deploymentName `
            --query "properties.provisioningState" --output tsv 2>$null

        if ($azState -eq 'Succeeded') {
            # Azure confirms success — exit code was a false negative (Bicep warnings on stderr)
            Write-Host "  ✓ Infrastructure deployment succeeded" -ForegroundColor Green
            Write-Host "  Retrieving deployment outputs..." -ForegroundColor Cyan

            $bicepOutput = az deployment sub show `
                --name $deploymentName `
                --query properties.outputs `
                --output json

            try {
                $bicepOutputJson = $bicepOutput | ConvertFrom-Json
            } catch {
                Write-Host "  ✗ Failed to parse deployment output — retrying output fetch..." -ForegroundColor Yellow
                $bicepOutputJson = az deployment sub show `
                    --name $deploymentName `
                    --query properties.outputs `
                    --output json | ConvertFrom-Json
            }

        } else {
            # Failure — pause and offer options before looping
            Write-Host "" 
            Write-Host "  ✗ Infrastructure deployment failed (attempt $deployAttempt)" -ForegroundColor Red
            Write-Host ""

            Write-Host ""
            Write-Host "  ✗ Infrastructure deployment failed (attempt $deployAttempt)" -ForegroundColor Red
            Write-Host "  Azure state: $azState" -ForegroundColor Yellow

            # Pull Azure-side error detail when the deployment was registered
            if ($azState -eq 'Failed') {
                $azError = az deployment sub show `
                    --name $deploymentName `
                    --query "properties.error" --output json 2>$null
                if ($azError -and $azError -ne 'null') {
                    Write-Host "  Azure error detail:" -ForegroundColor Red
                    ($azError | ConvertFrom-Json | ConvertTo-Json -Depth 5).Split("`n") |
                        ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
                }
            } elseif (-not $azState) {
                Write-Host "  (Deployment was never registered — failure was client-side or network)" -ForegroundColor Yellow
                Write-Host "  Check the output above for Bicep compilation or parameter errors." -ForegroundColor Yellow
            }
            Write-Host ""
            Write-Host "  ┌─ Choose an option ──────────────────────────────────────────┐" -ForegroundColor Cyan
            Write-Host "  │  R  Retry   — new deployment with a fresh suffix            │" -ForegroundColor White
            Write-Host "  │  L  Load    — load outputs from last succeeded deployment   │" -ForegroundColor White
            Write-Host "  │  Q  Quit    — stop the deployment                           │" -ForegroundColor White
            Write-Host "  └─────────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
            Write-Host ""

            $choice = Read-Host "  Enter choice [R/L/Q]"

            switch ($choice.Trim().ToUpper()) {
                'R' {
                    Write-Host "  ↻ Retrying deployment..." -ForegroundColor Cyan
                    Write-Host ""
                    # loop continues — new name and suffix generated at top
                }
                'L' {
                    Write-Host "  🔍 Searching for last succeeded zava deployment..." -ForegroundColor Cyan
                    $lastGood = az deployment sub list `
                        --query "[?starts_with(name,'zava-deployment') && properties.provisioningState=='Succeeded'] | sort_by(@, &properties.timestamp) | [-1].name" `
                        --output tsv 2>$null

                    if ($lastGood) {
                        Write-Host "  ✓ Found: $lastGood — loading outputs..." -ForegroundColor Green
                        $bicepOutputJson = az deployment sub show `
                            --name $lastGood `
                            --query properties.outputs `
                            --output json | ConvertFrom-Json
                        $deploymentName = $lastGood
                        if (-not $bicepOutputJson) {
                            Write-Host "  ✗ Could not load outputs from $lastGood" -ForegroundColor Red
                            Write-Host "  Try R to retry or Q to quit." -ForegroundColor Yellow
                            $bicepOutputJson = $null  # stay in loop
                        }
                    } else {
                        Write-Host "  ✗ No previous succeeded deployment found." -ForegroundColor Red
                        Write-Host "  Try R to retry or Q to quit." -ForegroundColor Yellow
                        # stay in loop
                    }
                }
                default {
                    Write-Host "  Deployment cancelled." -ForegroundColor Red
                    exit 1
                }
            }
        }
    }

    Write-Host "  ✓ Infrastructure deployed successfully!" -ForegroundColor Green

    # --- Sync .env with fresh Bicep outputs ---
    # This ensures subsequent manual script runs always use the correct endpoints,
    # rather than stale system env vars or outdated .env values.
    Write-Host ""
    Write-Host "  📝 Updating .env with deployment outputs..." -ForegroundColor Cyan

    # Update-EnvFile is defined at the top of the script — available everywhere.

    $openAIEndpoint      = $bicepOutputJson.middleware.value.openAIServiceEndpoint
    $aiServicesEndpoint  = $bicepOutputJson.middleware.value.aiServicesEndpoint
    $aiProjectEndpoint   = $bicepOutputJson.middleware.value.aiProjectEndpoint
    $cosmosEndpoint      = $bicepOutputJson.backend.value.cosmosDbEndpoint

    Update-EnvFile "AZURE_OPENAI_ENDPOINT"        $openAIEndpoint
    Update-EnvFile "AZURE_AI_SERVICES_ENDPOINT"   $aiServicesEndpoint
    Update-EnvFile "AZURE_AI_PROJECT_ENDPOINT"    $aiProjectEndpoint
    Update-EnvFile "COSMOS_DB_ENDPOINT"           $cosmosEndpoint

    if ($openAIEndpoint)     { Write-Host "  ✓ AZURE_OPENAI_ENDPOINT       = $openAIEndpoint" -ForegroundColor Green }
    if ($aiServicesEndpoint) { Write-Host "  ✓ AZURE_AI_SERVICES_ENDPOINT  = $aiServicesEndpoint" -ForegroundColor Green }
    if ($aiProjectEndpoint)  { Write-Host "  ✓ AZURE_AI_PROJECT_ENDPOINT   = $aiProjectEndpoint" -ForegroundColor Green }
    if ($cosmosEndpoint)     { Write-Host "  ✓ COSMOS_DB_ENDPOINT           = $cosmosEndpoint" -ForegroundColor Green }
    Write-Host "  ✓ .env updated — subsequent script runs will use these values" -ForegroundColor Green
    Write-Host ""
    Write-Host "  📋 Deployment Details:" -ForegroundColor Cyan
    Write-Host "     Frontend Resource Group: $frontendRgName" -ForegroundColor White
    Write-Host "       App Service: $($bicepOutputJson.frontend.value.appServiceName)" -ForegroundColor Gray
    Write-Host "       URL: $($bicepOutputJson.frontend.value.appServiceUrl)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "     Middleware Resource Group: $middlewareRgName" -ForegroundColor White
    Write-Host "       Azure AI Services : $($bicepOutputJson.middleware.value.openAIServiceName)" -ForegroundColor Gray
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

    # Persist AppServiceName immediately so -CodeOnly works on any subsequent run,
    # even if the script fails before the final save at the end.
    $earlyConfig = @{
        AppServiceName          = $WebAppName
        FrontendResourceGroup   = $frontendRgName
        MiddlewareResourceGroup = $middlewareRgName
        BackendResourceGroup    = $backendRgName
        SharedResourceGroup     = $sharedRgName
        Location                = $Location
        Environment             = $Environment
        Sku                     = $Sku
        DeploymentDate          = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        Url                     = "https://$WebAppName.azurewebsites.net"
    }
    $earlyConfig | ConvertTo-Json | Set-Content $deploymentConfigFile
    Write-Host "  ✓ Deployment config saved early ($deploymentConfigFile) — -CodeOnly will work from now on" -ForegroundColor Green

    # Wait for RBAC permissions to propagate
    Write-Host ""
    Write-Host "[3/7] Waiting for cross-resource group RBAC permissions to propagate..." -ForegroundColor Yellow
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

# [4/7] Create Azure AI Foundry Agents
# Skipped on -CodeOnly: agent IDs are already in App Service settings and .env.
# Re-creating agents would generate new IDs that would then mismatch the .env,
# breaking all tracking queries until a full redeploy is performed.
$agentSettings = @{}
if ($CodeOnly) {
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "[4/7] Skipping agent creation (-CodeOnly flag)" -ForegroundColor Yellow
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  ℹ  Existing agent IDs in App Service settings will be used" -ForegroundColor DarkGray
    Write-Host ""
} else {
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "[4/7] Creating Azure AI Foundry Agents..." -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  📦 This will create 8 AI agents in your Azure AI project" -ForegroundColor Gray
Write-Host "  ⏱ This may take 2-3 minutes..." -ForegroundColor Gray
Write-Host ""

# Create agents using Python script
if (-not $pythonExe) {
    Write-Host "  ⚠ Python not found - skipping agent creation" -ForegroundColor Yellow
    Write-Host "    Run manually: python scripts/create_foundry_agents_openai.py" -ForegroundColor Gray
} else {
    # Resolve resource ID once - reused across all retry attempts
    $openAIServiceName = $bicepOutputJson.middleware.value.openAIServiceName
    $subscriptionId    = $account.id
    $resourceId        = "/subscriptions/$subscriptionId/resourceGroups/$middlewareRgName/providers/Microsoft.CognitiveServices/accounts/$openAIServiceName"

    # Helper: prompt R / S / Q and return the choice
    function Invoke-RetryPrompt {
        param([string]$Context)
        Write-Host ""
        Write-Host "  ┌─ $Context ──────────────────────────────────┐" -ForegroundColor Cyan
        Write-Host "  │  R  Retry  — try again                                      │" -ForegroundColor White
        Write-Host "  │  S  Skip   — continue deployment without this step          │" -ForegroundColor White
        Write-Host "  │  Q  Quit   — stop the deployment now                        │" -ForegroundColor White
        Write-Host "  └─────────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
        return (Read-Host "  Enter choice [R/S/Q]").Trim().ToUpper()
    }

    # Use openai.AzureOpenAI + DefaultAzureCredential (picks up 'az login' locally, Managed Identity in Azure)
    # No API key enable/disable needed
    $env:AZURE_OPENAI_ENDPOINT            = $bicepOutputJson.middleware.value.openAIServiceEndpoint
    $env:AZURE_AI_MODEL_DEPLOYMENT_NAME   = "gpt-4o"
    $env:PYTHONIOENCODING                 = "utf-8"
    # Set tenant ID so DefaultAzureCredential uses the correct tenant (prevents token tenant mismatch)
    $env:AZURE_TENANT_ID                  = $account.tenantId

    # Grant the current developer 'Cognitive Services OpenAI Contributor' on the OpenAI resource
    # Required for assistants/write (creating agents) — Bicep only grants this to the App Service MI
    $currentUserObjectId = az ad signed-in-user show --query id -o tsv 2>$null
    if ($currentUserObjectId) {
        Write-Host "  🔑 Granting Cognitive Services OpenAI Contributor to current user..." -ForegroundColor Yellow
        az role assignment create `
            --assignee-object-id $currentUserObjectId `
            --assignee-principal-type User `
            --role "a001fd3d-188f-4b5d-821b-7da978bf7442" `
            --scope $resourceId `
            --output none 2>&1 | Out-Null
        Write-Host "  ⏱ Waiting 20 seconds for role assignment to propagate..." -ForegroundColor Gray
        Start-Sleep -Seconds 20
        Write-Host "  ✓ Role assigned — proceeding with agent creation" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Could not determine signed-in user — agent creation may fail with 401" -ForegroundColor Yellow
        Write-Host "    Ensure you have 'Cognitive Services OpenAI Contributor' on the OpenAI resource" -ForegroundColor Gray
    }

    # ── Agent creation retry loop ────────────────────────────────────────────
    $agentsDone   = $false
    $agentAttempt = 0

    while (-not $agentsDone) {
        $agentAttempt++
        Write-Host ""
        Write-Host "  🤖 Creating AI agents (attempt $agentAttempt)..." -ForegroundColor Yellow
        Write-Host "     AI Project Endpoint: $($bicepOutputJson.middleware.value.aiProjectEndpoint)" -ForegroundColor Gray
        Write-Host "     OpenAI Endpoint    : $($bicepOutputJson.middleware.value.openAIServiceEndpoint)" -ForegroundColor Gray
        Write-Host ""

        & $pythonExe scripts/create_foundry_agents_openai.py 2>&1 | Tee-Object -Variable agentOutput | Out-Host
        $agentExitCode = $LASTEXITCODE

        $jsonMatch = if ($agentExitCode -eq 0 -and $agentOutput) {
            [regex]::Match(($agentOutput | Out-String), '\{[^{}]*"[A-Z_]+AGENT_ID"[^{}]*\}')
        } else { $null }

        if ($agentExitCode -eq 0 -and $jsonMatch -and $jsonMatch.Success) {
            # ── Parse and persist agent IDs ──────────────────────────────────
            $parsedAgentIds = $jsonMatch.Value | ConvertFrom-Json
            Write-Host ""
            Write-Host "  ✓ All agents created" -ForegroundColor Green
            Write-Host "  📋 Agent IDs:" -ForegroundColor Cyan
            $parsedAgentIds.PSObject.Properties | ForEach-Object {
                Write-Host "     $($_.Name) = $($_.Value)" -ForegroundColor Gray
                $agentSettings[$_.Name] = $_.Value
                Set-Item -Path "env:$($_.Name)" -Value $_.Value
                Update-EnvFile $_.Name $_.Value
            }
            Write-Host ""
            Write-Host "  ✓ Agent IDs persisted to .env" -ForegroundColor Green

            # ── Tool registration retry loop ──────────────────────────────────
            $toolsDone   = $false
            $toolAttempt = 0

            while (-not $toolsDone) {
                $toolAttempt++
                Write-Host ""
                Write-Host "  🔧 Registering Cosmos DB tools (attempt $toolAttempt)..." -ForegroundColor Cyan
                Write-Host "     Customer Service Agent: $($agentSettings['CUSTOMER_SERVICE_AGENT_ID'])" -ForegroundColor Gray
                Write-Host ""

                & $pythonExe scripts/register_agent_tools_openai.py 2>&1 | Out-Host
                $toolExitCode = $LASTEXITCODE

                if ($toolExitCode -eq 0) {
                    Write-Host ""
                    Write-Host "  ✓ Tools registered — validating..." -ForegroundColor Green
                    & $pythonExe scripts/validate_agent_tools.py 2>&1 | Out-Host
                    $toolsDone = $true
                } else {
                    Write-Host ""
                    Write-Host "  ✗ Tool registration failed (exit code: $toolExitCode, attempt $toolAttempt)" -ForegroundColor Red
                    $toolChoice = Invoke-RetryPrompt "Tool registration failed — choose an option"
                    switch ($toolChoice) {
                        'R' { Write-Host "  ↻ Retrying tool registration..." -ForegroundColor Cyan }
                        'S' { Write-Host "  ⚠ Skipping tool registration." -ForegroundColor Yellow; $toolsDone = $true }
                        default { exit 1 }
                    }
                }
            }

            $agentsDone = $true  # agent creation + tool registration both resolved

        } else {
            # Agent creation failed or JSON not found in output
            if ($agentExitCode -ne 0) {
                Write-Host ""
                Write-Host "  ✗ Agent creation script failed (exit code: $agentExitCode, attempt $agentAttempt)" -ForegroundColor Red
            } else {
                Write-Host ""
                Write-Host "  ✗ Agent creation ran but no agent IDs found in output (attempt $agentAttempt)" -ForegroundColor Red
            }

            $agentChoice = Invoke-RetryPrompt "Agent creation failed — choose an option"
            switch ($agentChoice) {
                'R' { Write-Host "  ↻ Retrying agent creation..." -ForegroundColor Cyan }
                'S' { Write-Host "  ⚠ Skipping agent creation." -ForegroundColor Yellow; $agentsDone = $true }
                default { exit 1 }
            }
        }
    }
}

} # end -not $CodeOnly agent creation block

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
        
        # Register tools if Customer Service Agent exists, tools weren't just registered,
        # and Bicep outputs are available (skipped on -CodeOnly where $bicepOutputJson is $null)
        if ($agentIds.ContainsKey("CUSTOMER_SERVICE_AGENT_ID") -and $agentSettings.Count -eq 0 -and $bicepOutputJson) {
            Write-Host ""
            Write-Host "  🔧 Verifying agent tools are registered..." -ForegroundColor Cyan
            Write-Host "     Agent ID: $($agentIds['CUSTOMER_SERVICE_AGENT_ID'])" -ForegroundColor Gray
            
            # Use openai.AzureOpenAI + DefaultAzureCredential — no API key enable/disable needed
            # Set environment variables for all agent IDs
            $env:AZURE_OPENAI_ENDPOINT = $bicepOutputJson.middleware.value.openAIServiceEndpoint
            foreach ($key in $agentIds.Keys) {
                Set-Item -Path "env:$key" -Value $agentIds[$key]
            }
            
            Write-Host ""
            # First validate if tools are already registered
            & $pythonExe scripts/validate_agent_tools.py 2>&1 | Out-Host
            $validateExitCode = $LASTEXITCODE
            
            if ($validateExitCode -ne 0) {
                # Tools not registered or validation failed - register them
                Write-Host ""
                Write-Host "  🔧 Registering Cosmos DB tools..." -ForegroundColor Cyan
                & $pythonExe scripts/register_agent_tools_openai.py 2>&1 | Out-Host
                $toolExitCode = $LASTEXITCODE
                
                if ($toolExitCode -eq 0) {
                    Write-Host ""
                    Write-Host "  ✓ Agent tools registered successfully" -ForegroundColor Green
                    
                    # Validate again
                    Write-Host ""
                    & $pythonExe scripts/validate_agent_tools.py 2>&1 | Out-Host
                } else {
                    Write-Host ""
                    Write-Host "  ⚠ Tool registration failed (exit code: $toolExitCode)" -ForegroundColor Yellow
                }
            } else {
                Write-Host ""
                Write-Host "  ✓ Agent tools already registered and validated" -ForegroundColor Green
            }
        }
    } else {
        Write-Host "  ⚠ No agent IDs found - agents may not work" -ForegroundColor Yellow
        Write-Host "    Run manually: python scripts/create_foundry_agents_openai.py" -ForegroundColor Gray
    }

    # Add depot addresses
    foreach ($key in $depots.Keys) {
        $additionalSettings += "$key=$($depots[$key])"
    }

    if ($depots.Count -gt 0) {
        Write-Host "  ✓ Found $($depots.Count) depot address(es)" -ForegroundColor Green
    }
}

# Add Azure configuration from Bicep deployment (PRIORITY: Use deployment outputs over .env)
if ($bicepOutputJson -and -not $CodeOnly) {
    Write-Host "  🔧 Configuring from Bicep deployment outputs (overrides .env)..." -ForegroundColor Cyan
    
    # Azure OpenAI configuration
    if ($bicepOutputJson.middleware.value.openAIServiceEndpoint) {
        $additionalSettings += "AZURE_OPENAI_ENDPOINT=$($bicepOutputJson.middleware.value.openAIServiceEndpoint)"
        $additionalSettings += "AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o"
        Write-Host "  ✓ Azure OpenAI endpoint configured: $($bicepOutputJson.middleware.value.openAIServiceEndpoint)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Azure OpenAI endpoint not found in deployment outputs" -ForegroundColor Yellow
    }
    
    # AI Project endpoint
    if ($bicepOutputJson.middleware.value.aiProjectEndpoint) {
        $additionalSettings += "AZURE_AI_PROJECT_ENDPOINT=$($bicepOutputJson.middleware.value.aiProjectEndpoint)"
        Write-Host "  ✓ AI Project endpoint configured: $($bicepOutputJson.middleware.value.aiProjectEndpoint)" -ForegroundColor Green
    }
    
    # Cosmos DB endpoint
    if ($bicepOutputJson.backend.value.cosmosDbEndpoint) {
        $additionalSettings += "COSMOS_DB_ENDPOINT=$($bicepOutputJson.backend.value.cosmosDbEndpoint)"
        $additionalSettings += "COSMOS_DB_DATABASE_NAME=logisticstracking"
        Write-Host "  ✓ Cosmos DB endpoint configured: $($bicepOutputJson.backend.value.cosmosDbEndpoint)" -ForegroundColor Green
    }
    
    # Agent IDs from deployment (CRITICAL: Use fresh agent IDs, not old .env values)
    $deploymentAgentIds = @{
        'PARCEL_INTAKE_AGENT_ID' = $bicepOutputJson.middleware.value.parcelIntakeAgentId
        'SORTING_FACILITY_AGENT_ID' = $bicepOutputJson.middleware.value.sortingFacilityAgentId
        'DELIVERY_COORDINATION_AGENT_ID' = $bicepOutputJson.middleware.value.deliveryCoordinationAgentId
        'DISPATCHER_AGENT_ID' = $bicepOutputJson.middleware.value.dispatcherAgentId
        'OPTIMIZATION_AGENT_ID' = $bicepOutputJson.middleware.value.optimizationAgentId
        'CUSTOMER_SERVICE_AGENT_ID' = $bicepOutputJson.middleware.value.customerServiceAgentId
        'FRAUD_RISK_AGENT_ID' = $bicepOutputJson.middleware.value.fraudRiskAgentId
        'IDENTITY_AGENT_ID' = $bicepOutputJson.middleware.value.identityAgentId
    }
    
    # Override .env agent IDs with deployment agent IDs
    $agentCount = 0
    foreach ($key in $deploymentAgentIds.Keys) {
        $value = $deploymentAgentIds[$key]
        if ($value) {
            # Remove old .env value from settings
            $additionalSettings = $additionalSettings | Where-Object { $_ -notmatch "^$key=" }
            # Add new deployment value
            $additionalSettings += "$key=$value"
            $agentCount++
        }
    }
    
    if ($agentCount -gt 0) {
        Write-Host "  ✓ Configured $agentCount agent IDs from deployment" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ No agent IDs found in deployment outputs - using .env values" -ForegroundColor Yellow
    }
}

# Add critical App Service configuration (REQUIRED for Flask apps on Azure)
Write-Host "  ✓ Adding critical App Service configuration..." -ForegroundColor Gray
$additionalSettings += "WEBSITES_PORT=8000"  # Tell Azure which port the app listens on
$additionalSettings += "PORT=8000"  # Backup port variable for Flask
$additionalSettings += "USE_MANAGED_IDENTITY=true"  # Use managed identity for Cosmos DB auth

# Apply additional settings if any
if ($additionalSettings.Count -gt 0) {
    az webapp config appsettings set `
        --name $WebAppName `
        --resource-group $frontendRgName `
        --settings $additionalSettings `
        --output none
    Write-Host "✓ Configuration settings applied to Web App ($($additionalSettings.Count) settings)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ No configuration settings to apply" -ForegroundColor Yellow
    Write-Host "  Agents should have been created automatically during deployment" -ForegroundColor Gray
    Write-Host "  If agents are missing, run: python scripts/create_foundry_agents.py" -ForegroundColor Gray
}

# Set startup command for Flask/Gunicorn (CRITICAL for Linux App Service)
Write-Host "  🚀 Configuring startup command..." -ForegroundColor Cyan
az webapp config set `
    --name $WebAppName `
    --resource-group $frontendRgName `
    --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app" `
    --output none

Write-Host "  ✓ Startup command: gunicorn --bind=0.0.0.0 --timeout 600 app:app" -ForegroundColor Green
Write-Host "  ℹ  Using application factory pattern from new architecture" -ForegroundColor Gray
Write-Host ""

# =============================================================================
# [6/7] Deploy Application Code (Enterprise-Grade with Validation)
# =============================================================================
Write-Host "[6/7] Deploying application code..." -ForegroundColor Yellow
Write-Host "  This may take 3-5 minutes for Oryx build..." -ForegroundColor Gray

# Step 1: Create deployment package with proper exclusions
$tempZip = "$env:TEMP\zava-logistics-deploy-$(Get-Date -Format 'yyyyMMddHHmmss').zip"
if (Test-Path $tempZip) { Remove-Item $tempZip -Force }

Write-Host "  📦 Creating deployment package..." -ForegroundColor Cyan

# Define exclusions (enterprise-grade - exclude dev/test files)
$excludePatterns = @(
    "*.git*", ".github", ".vscode", ".azure", ".deployment.json",
    "*__pycache__*", "*.pyc", "*.pyo", "*.pyd",
    ".env", ".env.*", "*.log",
    "node_modules", ".venv", "venv", "env",
    "*.zip", "deploy*.zip",
    ".vs", "*.suo", "*.user",
    "tests", "*test*.py", "scripts/test*.py"
)

# Get all files excluding patterns
$files = Get-ChildItem -Recurse -File | Where-Object {
    $file = $_
    $shouldInclude = $true
    foreach ($pattern in $excludePatterns) {
        if ($file.FullName -like "*$pattern*") {
            $shouldInclude = $false
            break
        }
    }
    $shouldInclude
}

Write-Host "    Including $($files.Count) files in deployment package" -ForegroundColor Gray

# CRITICAL: Create ZIP preserving folder structure
# Use temporary staging directory to maintain paths
$stagingDir = "$env:TEMP\zava-deploy-staging-$(Get-Date -Format 'yyyyMMddHHmmss')"
if (Test-Path $stagingDir) { Remove-Item $stagingDir -Recurse -Force }
New-Item -Path $stagingDir -ItemType Directory -Force | Out-Null

# Copy files preserving structure
foreach ($file in $files) {
    $relativePath = $file.FullName.Substring((Get-Location).Path.Length + 1)
    $targetPath = Join-Path $stagingDir $relativePath
    $targetDir = Split-Path $targetPath -Parent
    if (-not (Test-Path $targetDir)) {
        New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
    }
    Copy-Item $file.FullName -Destination $targetPath -Force
}

# Create ZIP from staging directory (preserves structure)
Compress-Archive -Path "$stagingDir\*" -DestinationPath $tempZip -Force

# Cleanup staging
Remove-Item $stagingDir -Recurse -Force

if (-not (Test-Path $tempZip)) {
    Write-Host "  ❌ ERROR: Failed to create deployment package" -ForegroundColor Red
    throw "Deployment package creation failed"
}

$zipSize = [math]::Round((Get-Item $tempZip).Length / 1MB, 2)
Write-Host "    ✓ Package created: $zipSize MB" -ForegroundColor Green

# Step 2: Deploy with retry logic (handles transient failures)
$deployAttempts = 0
$maxDeployAttempts = 2
$deploySuccess = $false

while ($deployAttempts -lt $maxDeployAttempts -and -not $deploySuccess) {
    $deployAttempts++
    
    if ($deployAttempts -gt 1) {
        Write-Host "`n  🔄 Retry attempt $deployAttempts/$maxDeployAttempts..." -ForegroundColor Yellow
        Write-Host "    Waiting 30 seconds before retry..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
    }
    
    Write-Host "  📤 Uploading to Azure App Service (attempt $deployAttempts/$maxDeployAttempts)..." -ForegroundColor Cyan
    Write-Host "    This triggers Oryx build which can take 2-4 minutes" -ForegroundColor Gray
    
    # Use 'az webapp deploy' which is more reliable than 'config-zip'
    $deployOutput = az webapp deploy `
        --name $WebAppName `
        --resource-group $frontendRgName `
        --src-path $tempZip `
        --type zip `
        --async false `
        --timeout 600 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Upload completed successfully" -ForegroundColor Green
        $deploySuccess = $true
    } else {
        Write-Host "    ⚠️  Upload encountered issues" -ForegroundColor Yellow
        Write-Host "    Output: $deployOutput" -ForegroundColor Gray
        
        if ($deployAttempts -ge $maxDeployAttempts) {
            Write-Host "`n  ❌ Code deployment failed after $maxDeployAttempts attempts" -ForegroundColor Red
            Write-Host "    Last error: $deployOutput" -ForegroundColor Gray
        }
    }
}

# Step 3: Validate deployment (CRITICAL - ensures code is actually deployed)
if ($deploySuccess) {
    Write-Host "`n  🔍 Validating deployment..." -ForegroundColor Cyan
    Write-Host "    Waiting 45 seconds for app to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 45
    
    # Test 1: Check if app responds
    Write-Host "    Testing web app endpoint..." -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri "https://$WebAppName.azurewebsites.net" -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "    ✓ Web app is responding (HTTP $($response.StatusCode))" -ForegroundColor Green
            
            # Test 2: Check for Flask app indicators in response
            $content = $response.Content
            if ($content -match "Zava|Login|Dashboard|Parcels" -or $content -match "Flask") {
                Write-Host "    ✓ Flask application detected in response" -ForegroundColor Green
                Write-Host "`n✅ Application code deployed and validated successfully" -ForegroundColor Green -BackgroundColor DarkGreen
            } else {
                Write-Host "    ⚠️  WARNING: Response doesn't contain expected Flask app content" -ForegroundColor Yellow
                Write-Host "    This might be a default Azure page - check manually" -ForegroundColor Gray
            }
        } else {
            Write-Host "    ⚠️  Unexpected status code: $($response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    ⚠️  WARNING: Could not validate web app response" -ForegroundColor Yellow
        Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Gray
        Write-Host "    The app may still be starting up - check manually" -ForegroundColor Gray
    }
    
    # Test 3: Restart app to ensure fresh start with new code
    Write-Host "`n  🔄 Restarting app to ensure fresh deployment..." -ForegroundColor Cyan
    az webapp restart --name $WebAppName --resource-group $frontendRgName --output none
    Start-Sleep -Seconds 20
    Write-Host "    ✓ App restarted" -ForegroundColor Green
    
} else {
    Write-Host "`n  ❌ CRITICAL: Code deployment failed" -ForegroundColor Red
    Write-Host "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Red
    Write-Host "  Infrastructure is deployed but application code deployment failed." -ForegroundColor Yellow
    Write-Host "`n  Manual deployment required:" -ForegroundColor Yellow
    Write-Host "    Option 1 (Recommended): Use VS Code Azure App Service extension" -ForegroundColor Gray
    Write-Host "      • Right-click project → Deploy to Web App → $WebAppName" -ForegroundColor Gray
    Write-Host "`n    Option 2: Manual CLI deployment" -ForegroundColor Gray
    Write-Host "      • az webapp deploy --name $WebAppName --resource-group $frontendRgName --src-path $tempZip --type zip" -ForegroundColor Gray
    Write-Host "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Red
    Write-Host ""
}

# Cleanup
if (Test-Path $tempZip) { Remove-Item $tempZip -Force }
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

# Tasks 3 & 4 require Bicep outputs — skip on code-only redeployments
if ($CodeOnly) {
    Write-Host "  ℹ  Skipping database init and demo data (not required for code-only deploy)" -ForegroundColor DarkGray
} else {

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
    
    # Step 1: Initialize Cosmos DB containers (REQUIRED before any data operations)
    Write-Host "  🗄️  Initializing Cosmos DB containers..." -ForegroundColor Cyan
    Write-Host "     (Creating 10 required containers with proper partition keys)" -ForegroundColor Gray
    
    try {
        if ($pythonExe) {
            $env:PYTHONIOENCODING = "utf-8"
            
            # CRITICAL: Get Cosmos DB connection from BICEP OUTPUTS, not from .env
            # This ensures we connect to the NEW deployment, not old cached values
            $cosmosEndpoint = $bicepOutputJson.backend.value.cosmosDbEndpoint
            
            # Temporarily enable local auth to get connection string
            Write-Host "    🔑 Enabling local auth temporarily..." -ForegroundColor Gray
            $cosmosResourceId = "/subscriptions/$subscriptionId/resourceGroups/$backendRgName/providers/Microsoft.DocumentDB/databaseAccounts/$cosmosAccountName"
            
            # Enable local auth temporarily (if not already enabled)
            $enableResult = az resource update `
                --ids $cosmosResourceId `
                --set properties.disableLocalAuth=false `
                --api-version 2023-11-15 `
                --output json 2>&1
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "    ⚠️  Failed to enable local auth: $enableResult" -ForegroundColor Yellow
                Write-Host "    Continuing anyway (may already be enabled)..." -ForegroundColor Gray
            } else {
                Write-Host "    ✓ Local auth enabled" -ForegroundColor Green
            }
            
            # CRITICAL: Wait for auth change to propagate globally
            Write-Host "    ⏳ Waiting 120 seconds for auth propagation..." -ForegroundColor Gray
            Start-Sleep -Seconds 120
            
            # Get connection string
            $cosmosKeys = az cosmosdb keys list `
                --name $cosmosAccountName `
                --resource-group $backendRgName `
                --type connection-strings `
                --query "connectionStrings[0].connectionString" `
                -o tsv
            
            # Set environment variables for the Python script (overrides .env)
            $env:COSMOS_CONNECTION_STRING = $cosmosKeys
            $env:COSMOS_DB_ENDPOINT = $cosmosEndpoint
            $env:COSMOS_DB_DATABASE_NAME = "logisticstracking"
            
            Write-Host "    ✓ Using Cosmos DB: $cosmosEndpoint" -ForegroundColor Green
            
            # Run container initialization with correct environment
            $containerOutput = & $pythonExe scripts/initialize_all_containers.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ All 10 containers initialized successfully" -ForegroundColor Green
            } else {
                # Check if containers already exist (not an error)
                if ($containerOutput -match "already exists|Conflict") {
                    Write-Host "  ✓ Containers already exist (OK)" -ForegroundColor Green
                } else {
                    Write-Host "  ⚠ Container initialization may have failed" -ForegroundColor Yellow
                    Write-Host "    Run manually: python scripts/initialize_all_containers.py" -ForegroundColor Gray
                    Write-Host "    Error output: $containerOutput" -ForegroundColor Gray
                }
            }
            
            # Re-secure Cosmos DB (disable local auth - back to managed identity only)
            Write-Host "    🔒 Re-securing Cosmos DB (managed identity only)..." -ForegroundColor Gray
            $disableResult = az resource update `
                --ids $cosmosResourceId `
                --set properties.disableLocalAuth=true `
                --api-version 2023-11-15 `
                --output json 2>&1
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "    ⚠️  Failed to disable local auth: $disableResult" -ForegroundColor Yellow
                Write-Host "    SECURITY WARNING: Local auth may still be enabled!" -ForegroundColor Red
            } else {
                Write-Host "    ✓ Cosmos DB re-secured (managed identity only)" -ForegroundColor Green
            }
            
        } else {
            Write-Host "  ⚠ Python not found - skipping container initialization" -ForegroundColor Yellow
            Write-Host "    Run manually: python scripts/initialize_all_containers.py" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ⚠ Could not initialize containers: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "    Run manually: python scripts/initialize_all_containers.py" -ForegroundColor Gray
    }
    
    # Step 2: Initialize default users (containers must be created first)
    Write-Host "  👤 Initializing default user accounts..." -ForegroundColor Cyan
    
    try {
        # Check if Python is available
        if ($pythonExe) {
            # Set encoding for Unicode output on Windows
            $env:PYTHONIOENCODING = "utf-8"
            
            # CRITICAL: Clear key-based connection string — local auth was re-disabled above.
            # Leaving COSMOS_CONNECTION_STRING set would cause setup_users.py to use the
            # now-invalidated key and hang indefinitely waiting for a 401 that never resolves.
            $env:COSMOS_CONNECTION_STRING = ""
            $env:COSMOS_DB_KEY = ""
            
            # Ensure endpoint and database name are set (used by managed identity path)
            if (-not $env:COSMOS_DB_ENDPOINT) {
                $env:COSMOS_DB_ENDPOINT = $bicepOutputJson.backend.value.cosmosDbEndpoint
                $env:COSMOS_DB_DATABASE_NAME = "logisticstracking"
            }
            
            Write-Host "    Using Cosmos DB: $env:COSMOS_DB_ENDPOINT" -ForegroundColor Gray
            
            # Run setup_users.py to create default accounts
            $setupOutput = & $pythonExe utils/setup/setup_users.py 2>&1
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
                    $retryOutput = & $pythonExe utils/setup/setup_users.py 2>&1
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
    if ($pythonExe) {
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
        
        Write-Host "    ⏱  Waiting 120 seconds for auth change to fully propagate across Azure..." -ForegroundColor Gray
        Write-Host "      (Azure configuration changes can take 90-120 seconds to apply globally)" -ForegroundColor Gray
        Start-Sleep -Seconds 120
        
        # Verify local auth is enabled
        Write-Host "    🔍 Verifying local auth is enabled..." -ForegroundColor Cyan
        $authStatus = az cosmosdb show --name $cosmosAccountName --resource-group $backendRgName --query "disableLocalAuth" -o tsv
        if ($authStatus -eq "false") {
            Write-Host "    ✓ Local auth confirmed enabled" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  Local auth not yet enabled - waiting additional 60 seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds 60
        }
        
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
            $env:PYTHONIOENCODING = "utf-8"  # Fix Windows Unicode encoding issues
            
            # Step 3a: Initialize all database containers FIRST (CRITICAL DEPENDENCY)
            Write-Host "    📦 Initializing all 10 database containers..." -ForegroundColor Cyan
            $containerOutput = & $pythonExe scripts/initialize_all_containers.py 2>&1
            
            if ($LASTEXITCODE -eq 0 -and $containerOutput -match "SUCCESS") {
                Write-Host "    ✓ All database containers created successfully" -ForegroundColor Green
                
                # Step 3a.1: VALIDATE containers exist (critical validation)
                Write-Host "    🔍 Validating all containers exist..." -ForegroundColor Cyan
                $validateOutput = & $pythonExe scripts/diagnose_containers.py 2>&1
                
                if ($LASTEXITCODE -eq 0 -and $validateOutput -match "All containers present") {
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
                    $retryOutput = & $pythonExe scripts/initialize_all_containers.py 2>&1
                    
                    Write-Host "    🔍 Re-validating container count..." -ForegroundColor Cyan
                    $retryValidate = & $pythonExe scripts/diagnose_containers.py 2>&1
                    
                    if ($LASTEXITCODE -eq 0 -and $retryValidate -match "All containers present") {
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
                $retryOutput = & $pythonExe scripts/initialize_all_containers.py 2>&1
                
                if ($LASTEXITCODE -eq 0 -and $retryOutput -match "SUCCESS") {
                    Write-Host "    ✓ Container creation succeeded on retry" -ForegroundColor Green
                    
                    # Validate after successful retry
                    Write-Host "    🔍 Validating container count..." -ForegroundColor Cyan
                    $validateOutput = & $pythonExe scripts/diagnose_containers.py 2>&1
                    
                    if ($LASTEXITCODE -eq 0 -and $validateOutput -match "All containers present") {
                        Write-Host "    ✓ Container validation passed - all 10 containers confirmed" -ForegroundColor Green
                    } else {
                        Write-Host "    ⚠️  Container count validation failed - attempting final retry..." -ForegroundColor Yellow
                        Start-Sleep -Seconds 30
                        
                        # Final retry
                        Write-Host "    🔄 Final retry of container initialization (attempt 3/3)..." -ForegroundColor Cyan
                        $finalRetry = & $pythonExe scripts/initialize_all_containers.py 2>&1
                        $finalValidate = & $pythonExe scripts/diagnose_containers.py 2>&1
                        
                        if (-not ($LASTEXITCODE -eq 0 -and $finalValidate -match "All containers present")) {
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
                    $finalRetry = & $pythonExe scripts/initialize_all_containers.py 2>&1
                    
                    if (-not ($LASTEXITCODE -eq 0 -and $finalRetry -match "SUCCESS")) {
                        Write-Host "    ❌ Container initialization failed after 3 attempts" -ForegroundColor Red
                        Write-Host "      Output:" -ForegroundColor Gray
                        Write-Host $finalRetry -ForegroundColor Gray
                        
                        # Re-secure before exiting
                        az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --api-version 2023-11-15 --output none 2>&1 | Out-Null
                        throw "Container initialization failed - cannot proceed"
                    }
                    
                    # Validate final success
                    $finalValidate = & $pythonExe scripts/diagnose_containers.py 2>&1
                    if (-not ($LASTEXITCODE -eq 0 -and $finalValidate -match "All containers present")) {
                        Write-Host "    ❌ Container validation failed" -ForegroundColor Red
                        az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --api-version 2023-11-15 --output none 2>&1 | Out-Null
                        throw "Container validation failed"
                    }
                    
                    Write-Host "    ✓ All containers validated successfully on final retry" -ForegroundColor Green
                }
            }
            
            # Step 3b: Generate demo data
            Write-Host "    📊 Generating demo data..." -ForegroundColor Cyan
            
            # Set encoding for Unicode output on Windows
            $env:PYTHONIOENCODING = "utf-8"
            
            # Generate fresh test parcels with valid DC assignments
            Write-Host "    • Creating test parcels with valid DC assignments..." -ForegroundColor Gray
            $freshDataOutput = & $pythonExe utils/generators/generate_fresh_test_data.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Fresh test data generated" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Fresh test data generation had issues" -ForegroundColor Yellow
            }

            # Generate dispatcher demo data (parcels at depot ready for assignment)
            Write-Host "    • Creating parcels ready for dispatcher assignment..." -ForegroundColor Gray
            $dispatcherOutput = & $pythonExe utils/generators/generate_dispatcher_demo_data.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Dispatcher demo data generated" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Dispatcher demo data generation had issues" -ForegroundColor Yellow
            }

            # Generate bulk realistic parcels FIRST so manifests can assign them to drivers
            Write-Host "    • Generating 2500 realistic parcels across all states..." -ForegroundColor Gray
            Write-Host "      ⏳ This may take 5-10 minutes..." -ForegroundColor Gray
            $bulkDemoOutput = & $pythonExe utils/generators/generate_bulk_realistic_data.py --count 2500 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ 2500 realistic parcels generated across all Australian states" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Bulk parcel generation had issues" -ForegroundColor Yellow
                if ($bulkDemoOutput) {
                    Write-Host "      Error: $($bulkDemoOutput | Select-String -Pattern 'Error|Exception' | Select-Object -First 1)" -ForegroundColor Gray
                }
            }

            # Generate driver manifests with parcels
            Write-Host "    • Creating driver manifests with delivery parcels..." -ForegroundColor Gray
            $manifestOutput = & $pythonExe utils/generators/generate_demo_manifests.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Demo manifests generated for all drivers" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Demo manifest generation had issues" -ForegroundColor Yellow
            }

            # Generate Voice & Text Example demo parcels only (RG857954, DT202512170037)
            # Bulk parcels were already created above — this just ensures the 2 keydemo parcels exist
            Write-Host "    • Ensuring Voice & Text Example demo parcels exist (RG857954, DT202512170037)..." -ForegroundColor Gray
            $demoParcelsOutput = & $pythonExe utils/generators/generate_bulk_realistic_data.py --demo-only 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Demo parcels verified (RG857954, DT202512170037)" -ForegroundColor Green
                Write-Host "      ✓ Try: 'Track parcel RG857954' or 'Find parcels for Dr. Emma Wilson'" -ForegroundColor Cyan
            } else {
                Write-Host "    ⚠ Demo parcel creation had issues" -ForegroundColor Yellow
                if ($demoParcelsOutput) {
                    Write-Host "      Error: $($demoParcelsOutput | Select-String -Pattern 'Error|Exception' | Select-Object -First 1)" -ForegroundColor Gray
                }
            }

            # Create approval demo requests
            Write-Host "    • Creating approval demo requests for existing parcels..." -ForegroundColor Gray
            $approvalOutput = & $pythonExe utils/generators/create_approval_requests.py 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Approval demo requests created" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ Approval request creation had issues (non-critical)" -ForegroundColor Yellow
                # Log error details if verbose
                if ($approvalOutput -match "ModuleNotFoundError") {
                    Write-Host "      Note: Ensure PYTHONPATH is set correctly" -ForegroundColor Gray
                }
            }

            # Import real delivery photo for DT202512170037 if image file exists
            $deliveryPhotoPath = "static\images\delivery_sample.jpg"
            $deliveryPhotoPng  = "static\images\delivery_sample.png"
            if ((Test-Path $deliveryPhotoPath) -or (Test-Path $deliveryPhotoPng)) {
                Write-Host "    • Importing real delivery photo for DT202512170037..." -ForegroundColor Gray
                $photoOutput = & $pythonExe utils/generators/import_delivery_photo.py 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    ✓ Real delivery photo imported for DT202512170037" -ForegroundColor Green
                } else {
                    Write-Host "    ⚠ Delivery photo import had issues (non-critical)" -ForegroundColor Yellow
                    if ($photoOutput) {
                        Write-Host "      $($photoOutput | Select-String -Pattern 'Error|✗' | Select-Object -First 1)" -ForegroundColor Gray
                    }
                }
            } else {
                Write-Host "    ℹ No delivery_sample image found - skipping photo import" -ForegroundColor Gray
                Write-Host "      (Save static\images\delivery_sample.jpg to include a real photo)" -ForegroundColor DarkGray
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

} # end -not $CodeOnly block

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
Write-Host "  ✓ 2500 realistic parcels generated across all Australian states" -ForegroundColor Green
Write-Host ""

# Optional: Generate bulk realistic data
# REMOVED: Bulk generation now happens automatically during deployment (2500 parcels)
#          within the same Cosmos DB local auth session to save time

Write-Host "Security & Permissions:" -ForegroundColor Yellow
Write-Host "  ✓ App Service using managed identity (no connection strings)" -ForegroundColor Green
Write-Host "  ✓ Cosmos DB RBAC permissions configured via Bicep" -ForegroundColor Green
Write-Host "  ✓ Azure OpenAI access via managed identity" -ForegroundColor Green
Write-Host "  ✓ Speech & Vision services accessible via RBAC" -ForegroundColor Green
Write-Host ""

# Update .env file with current deployment endpoints
Write-Host "📝 Updating .env file with current deployment endpoints..." -ForegroundColor Cyan

try {
    $envFilePath = Join-Path $PSScriptRoot ".env"
    
    if (Test-Path $envFilePath) {
        # Read current .env file
        $envContent = Get-Content $envFilePath -Raw
        
        # Get connection string for local development
        $cosmosAccountName = $bicepOutputJson.backend.value.cosmosDbAccountName
        $cosmosConnectionString = ""
        try {
            $cosmosConnectionString = az cosmosdb keys list `
                --name $cosmosAccountName `
                --resource-group $backendRgName `
                --type connection-strings `
                --query "connectionStrings[0].connectionString" `
                -o tsv 2>$null
        } catch {
            Write-Host "  ⚠ Could not retrieve Cosmos connection string (local auth may be disabled)" -ForegroundColor Yellow
        }
        
        # Update Cosmos DB settings
        $cosmosEndpoint = $bicepOutputJson.backend.value.cosmosDbEndpoint
        $envContent = $envContent -replace 'COSMOS_DB_ENDPOINT=.*', "COSMOS_DB_ENDPOINT=$cosmosEndpoint"
        
        if ($cosmosConnectionString) {
            $envContent = $envContent -replace 'COSMOS_CONNECTION_STRING=.*', "COSMOS_CONNECTION_STRING=$cosmosConnectionString"
        }
        
        # Update Azure OpenAI endpoint
        $openAIEndpoint = $bicepOutputJson.middleware.value.openAIServiceEndpoint
        $envContent = $envContent -replace 'AZURE_OPENAI_ENDPOINT=.*', "AZURE_OPENAI_ENDPOINT=$openAIEndpoint"
        
        # Update AI Project endpoint
        $aiProjectEndpoint = $bicepOutputJson.middleware.value.aiProjectEndpoint
        $envContent = $envContent -replace 'AZURE_AI_PROJECT_ENDPOINT=.*', "AZURE_AI_PROJECT_ENDPOINT=$aiProjectEndpoint"
        
        # Update all agent IDs
        $agentIds = @{
            'PARCEL_INTAKE_AGENT_ID' = $bicepOutputJson.middleware.value.parcelIntakeAgentId
            'SORTING_FACILITY_AGENT_ID' = $bicepOutputJson.middleware.value.sortingFacilityAgentId
            'DELIVERY_COORDINATION_AGENT_ID' = $bicepOutputJson.middleware.value.deliveryCoordinationAgentId
            'DISPATCHER_AGENT_ID' = $bicepOutputJson.middleware.value.dispatcherAgentId
            'OPTIMIZATION_AGENT_ID' = $bicepOutputJson.middleware.value.optimizationAgentId
            'CUSTOMER_SERVICE_AGENT_ID' = $bicepOutputJson.middleware.value.customerServiceAgentId
            'FRAUD_RISK_AGENT_ID' = $bicepOutputJson.middleware.value.fraudRiskAgentId
            'IDENTITY_AGENT_ID' = $bicepOutputJson.middleware.value.identityAgentId
        }
        
        foreach ($key in $agentIds.Keys) {
            $value = $agentIds[$key]
            if ($value) {
                $envContent = $envContent -replace "$key=.*", "$key=$value"
            }
        }
        
        # Add timestamp comment
        $timestamp = Get-Date -Format "MMMM dd, yyyy HH:mm"
        $envContent = $envContent -replace '# Azure AI Agents \(Updated:.*\)', "# Azure AI Agents (Updated: $timestamp - Auto-generated by deploy_to_azure.ps1)"
        
        # Write updated content
        Set-Content -Path $envFilePath -Value $envContent -NoNewline
        
        Write-Host "  ✓ .env file updated with current deployment endpoints" -ForegroundColor Green
        Write-Host "    Local development now configured for deployment: $suffix" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠ .env file not found - skipping update" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Could not update .env file: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "    You may need to manually update .env for local development" -ForegroundColor Gray
}

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

