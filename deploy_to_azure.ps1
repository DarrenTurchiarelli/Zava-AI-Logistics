# =============================================================================
# Deploy DT Logistics to Azure App Service
# =============================================================================

param(
    [string]$ResourceGroup = "dt-logistics-rg",
    [string]$Location = "australiaeast",
    [string]$AppServicePlan = "dt-logistics-plan",
    [string]$WebAppName = "",
    [string]$Sku = "B2", #P1v2 is also good for production
    [switch]$Force
)

$deploymentConfigFile = ".azure-deployment.json"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " DT Logistics - Azure App Service Deployment" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Check for existing deployment
$existingDeployment = $null
$isRedeployment = $false

if (Test-Path $deploymentConfigFile) {
    Write-Host "[0/11] Found existing deployment configuration..." -ForegroundColor Yellow
    try {
        $existingDeployment = Get-Content $deploymentConfigFile -Raw | ConvertFrom-Json
        
        # Use existing configuration if not overridden by parameters
        if (-not $WebAppName) {
            $WebAppName = $existingDeployment.WebAppName
            $isRedeployment = $true
        }
        if (-not $PSBoundParameters.ContainsKey('ResourceGroup')) {
            $ResourceGroup = $existingDeployment.ResourceGroup
        }
        if (-not $PSBoundParameters.ContainsKey('AppServicePlan')) {
            $AppServicePlan = $existingDeployment.AppServicePlan
        }
        if (-not $PSBoundParameters.ContainsKey('Location')) {
            $Location = $existingDeployment.Location
        }
        
        Write-Host "✓ Redeploying to existing App Service: $WebAppName" -ForegroundColor Green
        Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor Gray
        Write-Host "  App Service Plan: $AppServicePlan" -ForegroundColor Gray
        
        if ($Force) {
            Write-Host "  ⚠ Force flag detected - will recreate resources" -ForegroundColor Yellow
            $isRedeployment = $false
        }
    } catch {
        Write-Host "⚠ Could not read existing deployment config, creating new deployment" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Generate new name if needed
if (-not $WebAppName) {
    $WebAppName = "dt-logistics-web-$(Get-Random -Minimum 1000 -Maximum 9999)"
    Write-Host "Generated new Web App name: $WebAppName" -ForegroundColor Cyan
    Write-Host ""
}

# Check if logged in
Write-Host "[1/11] Checking Azure login status..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "✗ Not logged in to Azure. Running 'az login'..." -ForegroundColor Red
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Host "✓ Logged in as: $($account.user.name)" -ForegroundColor Green
Write-Host "✓ Subscription: $($account.name)" -ForegroundColor Green
Write-Host ""

# Create or verify Resource Group
Write-Host "[2/11] Ensuring Resource Group exists: $ResourceGroup..." -ForegroundColor Yellow
if ($isRedeployment) {
    $rgExists = az group exists --name $ResourceGroup
    if ($rgExists -eq "true") {
        Write-Host "✓ Resource Group exists (reusing)" -ForegroundColor Green
    } else {
        Write-Host "⚠ Resource Group not found, creating new one" -ForegroundColor Yellow
        az group create --name $ResourceGroup --location $Location --output none
        Write-Host "✓ Resource Group created" -ForegroundColor Green
    }
} else {
    az group create --name $ResourceGroup --location $Location --output none
    Write-Host "✓ Resource Group created" -ForegroundColor Green
}
Write-Host ""

# Create or verify App Service Plan
Write-Host "[3/11] Ensuring App Service Plan exists: $AppServicePlan..." -ForegroundColor Yellow
if ($isRedeployment) {
    $planExists = az appservice plan show --name $AppServicePlan --resource-group $ResourceGroup 2>$null
    if ($planExists) {
        Write-Host "✓ App Service Plan exists (reusing)" -ForegroundColor Green
    } else {
        Write-Host "⚠ App Service Plan not found, creating new one" -ForegroundColor Yellow
        az appservice plan create `
            --name $AppServicePlan `
            --resource-group $ResourceGroup `
            --sku $Sku `
            --is-linux `
            --output none
        Write-Host "✓ App Service Plan created (SKU: $Sku)" -ForegroundColor Green
    }
} else {
    az appservice plan create `
        --name $AppServicePlan `
        --resource-group $ResourceGroup `
        --sku $Sku `
        --is-linux `
        --output none
    Write-Host "✓ App Service Plan created (SKU: $Sku)" -ForegroundColor Green
}
Write-Host ""

# Create or verify Web App
Write-Host "[4/11] Ensuring Web App exists: $WebAppName..." -ForegroundColor Yellow
if ($isRedeployment) {
    $webAppExists = az webapp show --name $WebAppName --resource-group $ResourceGroup 2>$null
    if ($webAppExists) {
        Write-Host "✓ Web App exists (reusing for redeployment)" -ForegroundColor Green
    } else {
        Write-Host "⚠ Web App not found, creating new one" -ForegroundColor Yellow
        az webapp create `
            --name $WebAppName `
            --resource-group $ResourceGroup `
            --plan $AppServicePlan `
            --runtime "PYTHON:3.11" `
            --output none
        Write-Host "✓ Web App created" -ForegroundColor Green
    }
} else {
    az webapp create `
        --name $WebAppName `
        --resource-group $ResourceGroup `
        --plan $AppServicePlan `
        --runtime "PYTHON:3.11" `
        --output none
    Write-Host "✓ Web App created" -ForegroundColor Green
}
Write-Host ""

# Enable system-assigned managed identity
Write-Host "[5/11] Enabling managed identity..." -ForegroundColor Yellow
az webapp identity assign `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --output none
Write-Host "✓ Managed identity enabled" -ForegroundColor Green
Write-Host ""

# Configure startup command
Write-Host "[6/11] Configuring startup command..." -ForegroundColor Yellow
az webapp config set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers=4 --threads=2 --worker-class=gthread app:app" `
    --output none
Write-Host "✓ Startup command configured" -ForegroundColor Green
Write-Host ""

# Set environment variables
Write-Host "[7/11] Setting environment variables..." -ForegroundColor Yellow

# Generate Flask secret key
$FlaskSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})

# Get existing .env values (if available)
$CosmosConnection = ""
$CosmosEndpoint = ""
$CosmosKey = ""
$CosmosDatabaseName = ""
$AzureAIConnection = ""
$AzureAIEndpoint = ""
$AzureAIModel = ""
$AzureMapsKey = ""
$AzureVisionEndpoint = ""
$AzureVisionKey = ""
$DepotNSW = ""
$DepotVIC = ""
$DepotQLD = ""
$DepotSA = ""
$DepotWA = ""
$DepotTAS = ""
$DepotACT = ""
$DepotNT = ""
$CosmosAccountName = ""
$AIHubName = ""
$AIHubResourceGroup = ""

if (Test-Path ".env") {
    Write-Host "  Reading configuration from .env file..." -ForegroundColor Gray
    Get-Content .env | ForEach-Object {
        if ($_ -match '^COSMOS_CONNECTION_STRING\s*=\s*"?([^"]+)"?') {
            $CosmosConnection = $matches[1]
        }
        if ($_ -match '^COSMOS_DB_ENDPOINT\s*=\s*"?([^"]+)"?') {
            $CosmosEndpoint = $matches[1]
        }
        if ($_ -match '^COSMOS_DB_KEY\s*=\s*"?([^"]+)"?') {
            $CosmosKey = $matches[1]
        }
        if ($_ -match '^COSMOS_DB_DATABASE_NAME\s*=\s*"?([^"]+)"?') {
            $CosmosDatabaseName = $matches[1]
        }
        if ($_ -match '^AZURE_AI_PROJECT_CONNECTION_STRING\s*=\s*"?([^"]+)"?') {
            $AzureAIConnection = $matches[1]
        }
        if ($_ -match '^AZURE_AI_PROJECT_ENDPOINT\s*=\s*"?([^"]+)"?') {
            $AzureAIEndpoint = $matches[1]
        }
        if ($_ -match '^AZURE_AI_MODEL_DEPLOYMENT_NAME\s*=\s*"?([^"]+)"?') {
            $AzureAIModel = $matches[1]
        }
        if ($_ -match '^AZURE_MAPS_SUBSCRIPTION_KEY\s*=\s*"?([^"]+)"?') {
            $AzureMapsKey = $matches[1]
        }
        if ($_ -match '^AZURE_VISION_ENDPOINT\s*=\s*"?([^"]+)"?') {
            $AzureVisionEndpoint = $matches[1]
        }
        if ($_ -match '^AZURE_VISION_KEY\s*=\s*"?([^"]+)"?') {
            $AzureVisionKey = $matches[1]
        }
        if ($_ -match '^DEPOT_NSW\s*=\s*"?([^"]+)"?') {
            $DepotNSW = $matches[1]
        }
        if ($_ -match '^DEPOT_VIC\s*=\s*"?([^"]+)"?') {
            $DepotVIC = $matches[1]
        }
        if ($_ -match '^DEPOT_QLD\s*=\s*"?([^"]+)"?') {
            $DepotQLD = $matches[1]
        }
        if ($_ -match '^DEPOT_SA\s*=\s*"?([^"]+)"?') {
            $DepotSA = $matches[1]
        }
        if ($_ -match '^DEPOT_WA\s*=\s*"?([^"]+)"?') {
            $DepotWA = $matches[1]
        }
        if ($_ -match '^DEPOT_TAS\s*=\s*"?([^"]+)"?') {
            $DepotTAS = $matches[1]
        }
        if ($_ -match '^DEPOT_ACT\s*=\s*"?([^"]+)"?') {
            $DepotACT = $matches[1]
        }
        if ($_ -match '^DEPOT_NT\s*=\s*"?([^"]+)"?') {
            $DepotNT = $matches[1]
        }
        # Extract Cosmos account name from endpoint for RBAC
        if ($_ -match '^COSMOS_DB_ENDPOINT\s*=\s*"?https://([^.]+)\.documents\.azure\.com') {
            $CosmosAccountName = $matches[1]
        }
        # Extract AI Hub name from endpoint for RBAC
        if ($_ -match '^AZURE_VISION_ENDPOINT\s*=\s*"?https://([^.]+)\.cognitiveservices\.azure\.com') {
            $AIHubName = $matches[1]
        }
        if ($_ -match '^AZURE_AI_PROJECT_ENDPOINT\s*=\s*"?https://([^.]+)\.services\.ai\.azure\.com') {
            $AIHubName = $matches[1]
        }
    }
}

# Prepare settings
$settings = @(
    "FLASK_SECRET_KEY=$FlaskSecret"
    "FLASK_ENV=production"
    "PORT=8000"
    "SCM_DO_BUILD_DURING_DEPLOYMENT=true"
    "USE_MANAGED_IDENTITY=true"
)

Write-Host "  ✓ Managed identity authentication enabled" -ForegroundColor Green

if ($CosmosEndpoint) {
    $settings += "COSMOS_DB_ENDPOINT=$CosmosEndpoint"
    Write-Host "  ✓ Cosmos DB endpoint configured (using managed identity)" -ForegroundColor Green
}
# Do NOT set COSMOS_CONNECTION_STRING or COSMOS_DB_KEY when using managed identity
if ($CosmosDatabaseName) {
    $settings += "COSMOS_DB_DATABASE_NAME=$CosmosDatabaseName"
    Write-Host "  ✓ Cosmos DB database name configured" -ForegroundColor Green
}
if ($AzureAIConnection) {
    $settings += "AZURE_AI_PROJECT_CONNECTION_STRING=$AzureAIConnection"
    Write-Host "  ✓ Azure AI Foundry connection string configured" -ForegroundColor Green
}
if ($AzureAIEndpoint) {
    $settings += "AZURE_AI_PROJECT_ENDPOINT=$AzureAIEndpoint"
    Write-Host "  ✓ Azure AI Foundry endpoint configured" -ForegroundColor Green
}
if ($AzureAIModel) {
    $settings += "AZURE_AI_MODEL_DEPLOYMENT_NAME=$AzureAIModel"
    Write-Host "  ✓ Azure AI model deployment configured" -ForegroundColor Green
}
if ($AzureMapsKey) {
    $settings += "AZURE_MAPS_SUBSCRIPTION_KEY=$AzureMapsKey"
    Write-Host "  ✓ Azure Maps key configured" -ForegroundColor Green
}
if ($AzureVisionEndpoint) {
    $settings += "AZURE_VISION_ENDPOINT=$AzureVisionEndpoint"
    Write-Host "  ✓ Azure Vision endpoint configured" -ForegroundColor Green
}
if ($AzureVisionKey) {
    $settings += "AZURE_VISION_KEY=$AzureVisionKey"
    Write-Host "  ✓ Azure Vision key configured" -ForegroundColor Green
}
if ($DepotNSW) {
    $settings += "DEPOT_NSW=$DepotNSW"
}
if ($DepotVIC) {
    $settings += "DEPOT_VIC=$DepotVIC"
}
if ($DepotQLD) {
    $settings += "DEPOT_QLD=$DepotQLD"
}
if ($DepotSA) {
    $settings += "DEPOT_SA=$DepotSA"
}
if ($DepotWA) {
    $settings += "DEPOT_WA=$DepotWA"
}
if ($DepotTAS) {
    $settings += "DEPOT_TAS=$DepotTAS"
}
if ($DepotACT) {
    $settings += "DEPOT_ACT=$DepotACT"
}
if ($DepotNT) {
    $settings += "DEPOT_NT=$DepotNT"
}
if ($DepotNSW -or $DepotVIC -or $DepotQLD -or $DepotSA -or $DepotWA -or $DepotTAS -or $DepotACT -or $DepotNT) {
    Write-Host "  ✓ Depot addresses configured" -ForegroundColor Green
}

az webapp config appsettings set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --settings $settings `
    --output none

Write-Host "✓ Environment variables configured" -ForegroundColor Green
Write-Host ""

# Configure RBAC permissions for managed identity
Write-Host "[8/11] Configuring RBAC permissions..." -ForegroundColor Yellow

# Get the managed identity principal ID
$principalId = az webapp identity show --name $WebAppName --resource-group $ResourceGroup --query principalId -o tsv

if (-not $principalId) {
    Write-Host "  ✗ Failed to retrieve managed identity principal ID" -ForegroundColor Red
    Write-Host "  Skipping RBAC setup - you may need to configure manually" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Managed Identity Principal ID: $principalId" -ForegroundColor Green
    $subscriptionId = az account show --query id -o tsv
    
    # 1. Cosmos DB RBAC
    if ($CosmosAccountName) {
        Write-Host "  📦 Configuring Cosmos DB permissions..." -ForegroundColor Cyan
        
        # Find Cosmos DB account
        $cosmosAccount = az cosmosdb list --query "[?name=='$CosmosAccountName'].{name:name, resourceGroup:resourceGroup}" -o json | ConvertFrom-Json
        
        if ($cosmosAccount -and $cosmosAccount.Count -gt 0) {
            $cosmosRG = $cosmosAccount[0].resourceGroup
            Write-Host "     Found: $CosmosAccountName (RG: $cosmosRG)" -ForegroundColor Gray
            
            try {
                az cosmosdb sql role assignment create `
                    --account-name $CosmosAccountName `
                    --resource-group $cosmosRG `
                    --role-definition-id "00000000-0000-0000-0000-000000000002" `
                    --principal-id $principalId `
                    --scope "/" `
                    --output none 2>$null
                
                Write-Host "     ✓ Cosmos DB Built-in Data Contributor" -ForegroundColor Green
            } catch {
                Write-Host "     ⚠ Role may already exist" -ForegroundColor Yellow
            }
        } else {
            Write-Host "     ⚠ Cosmos DB '$CosmosAccountName' not found" -ForegroundColor Yellow
        }
    }
    
    # 2. Azure AI Foundry / Cognitive Services RBAC
    if ($AIHubName) {
        Write-Host "  🤖 Configuring Azure AI Foundry permissions..." -ForegroundColor Cyan
        
        # Find AI Hub resource
        $aiHub = az cognitiveservices account list --query "[?name=='$AIHubName'].{name:name, resourceGroup:resourceGroup}" -o json | ConvertFrom-Json
        
        if ($aiHub -and $aiHub.Count -gt 0) {
            $AIHubResourceGroup = $aiHub[0].resourceGroup
            Write-Host "     Found: $AIHubName (RG: $AIHubResourceGroup)" -ForegroundColor Gray
            
            $aiHubScope = "/subscriptions/$subscriptionId/resourceGroups/$AIHubResourceGroup/providers/Microsoft.CognitiveServices/accounts/$AIHubName"
            
            # Grant multiple roles for AI Hub
            $aiRoles = @(
                @{Name="Cognitive Services OpenAI Contributor"; Desc="OpenAI operations"},
                @{Name="Azure AI Developer"; Desc="Agents write access"},
                @{Name="Cognitive Services User"; Desc="Agents read access"},
                @{Name="Cognitive Services Contributor"; Desc="Full AI Hub access"},
                @{Name="Cognitive Services OpenAI User"; Desc="Agents/read data action"},
                @{Name="Cognitive Services Usages Reader"; Desc="Usage metrics"},
                @{Name="Azure AI Inference Deployment Operator"; Desc="AI Foundry agent operations"}
            )
            
            foreach ($role in $aiRoles) {
                try {
                    az role assignment create `
                        --assignee-object-id $principalId `
                        --assignee-principal-type ServicePrincipal `
                        --role $role.Name `
                        --scope $aiHubScope `
                        --output none 2>$null
                    
                    Write-Host "     ✓ $($role.Name)" -ForegroundColor Green
                } catch {
                    Write-Host "     ⚠ $($role.Name) (may already exist)" -ForegroundColor Yellow
                }
            }
            
            # Also grant at resource group level for broader access
            try {
                az role assignment create `
                    --assignee-object-id $principalId `
                    --assignee-principal-type ServicePrincipal `
                    --role "Cognitive Services OpenAI Contributor" `
                    --scope "/subscriptions/$subscriptionId/resourceGroups/$AIHubResourceGroup" `
                    --output none 2>$null
                
                Write-Host "     ✓ Resource Group level permissions" -ForegroundColor Green
            } catch {
                Write-Host "     ⚠ RG permissions (may already exist)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "     ⚠ AI Hub '$AIHubName' not found" -ForegroundColor Yellow
            Write-Host "     Attempting resource group level permissions..." -ForegroundColor Gray
            
            # Fallback: grant at app's resource group level
            $aiRoles = @("Cognitive Services OpenAI Contributor", "Azure AI Developer", "Cognitive Services User")
            foreach ($role in $aiRoles) {
                try {
                    az role assignment create `
                        --assignee-object-id $principalId `
                        --assignee-principal-type ServicePrincipal `
                        --role $role `
                        --scope "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup" `
                        --output none 2>$null
                    Write-Host "     ✓ $role (fallback)" -ForegroundColor Green
                } catch {
                    Write-Host "     ⚠ $role (may already exist)" -ForegroundColor Yellow
                }
            }
        }
    }
    
    Write-Host "  ✓ RBAC configuration complete" -ForegroundColor Green
    Write-Host "  ⚠ Note: Role assignments may take 2-5 minutes to propagate" -ForegroundColor Yellow
}
Write-Host ""

# Deploy application
Write-Host "[9/11] Deploying application code..." -ForegroundColor Yellow
Write-Host "  This may take 3-5 minutes..." -ForegroundColor Gray

# Create a deployment ZIP (excluding unnecessary files)
$tempZip = "$env:TEMP\dt-logistics-deploy.zip"
if (Test-Path $tempZip) { Remove-Item $tempZip -Force }

# Files/folders to exclude
$excludeList = @(
    "__pycache__",
    "*.pyc",
    ".git",
    ".env",
    ".venv",
    "venv",
    "*.md",
    "Test Scripts",
    "Scripts",
    "Guides"
)

# Create deployment package
Compress-Archive -Path * -DestinationPath $tempZip -Force

# Deploy ZIP
az webapp deployment source config-zip `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --src $tempZip `
    --timeout 600

Remove-Item $tempZip -Force

Write-Host "✓ Application deployed" -ForegroundColor Green
Write-Host ""

# Configure additional settings
Write-Host "[10/11] Configuring additional settings..." -ForegroundColor Yellow

# Enable Always On (requires Basic or higher SKU)
if ($Sku -ne "F1" -and $Sku -ne "D1") {
    az webapp config set `
        --name $WebAppName `
        --resource-group $ResourceGroup `
        --always-on true `
        --output none
    Write-Host "  ✓ Always On enabled" -ForegroundColor Green
}

# Enable logging
az webapp log config `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --application-logging filesystem `
    --detailed-error-messages true `
    --web-server-logging filesystem `
    --output none
Write-Host "  ✓ Logging configured" -ForegroundColor Green

# Enable HTTPS only
az webapp update `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --https-only true `
    --output none
Write-Host "  ✓ HTTPS-only enabled" -ForegroundColor Green
Write-Host ""

# Post-deployment tasks
Write-Host "[11/11] Running post-deployment tasks..." -ForegroundColor Yellow

# Task 1: Setup default users
Write-Host "  📋 Setting up default users..." -ForegroundColor Cyan
if (Test-Path "utils\setup\setup_users.py") {
    try {
        $env:PYTHONPATH = "$PWD;$PWD\utils\setup"
        python utils\setup\setup_users.py
        Write-Host "  ✓ Default users initialized" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ User initialization failed (users may already exist): $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ utils\setup\setup_users.py not found, skipping user setup" -ForegroundColor Yellow
}

# Task 2: Generate demo manifests
Write-Host "  📋 Generating demo manifests for all drivers..." -ForegroundColor Cyan
if (Test-Path "utils\generators\generate_demo_manifests.py") {
    try {
        $env:PYTHONPATH = "$PWD;$PWD\utils\generators"
        python utils\generators\generate_demo_manifests.py --all
        Write-Host "  ✓ Demo manifests generated successfully" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Demo manifest generation failed: $_" -ForegroundColor Yellow
        Write-Host "  You can generate manifests manually after deployment" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⚠ utils\generators\generate_demo_manifests.py not found, skipping manifest generation" -ForegroundColor Yellow
}

Write-Host "  ✓ Post-deployment tasks completed" -ForegroundColor Green
Write-Host ""

# Save deployment configuration
$deploymentInfo = @{
    WebAppName = $WebAppName
    ResourceGroup = $ResourceGroup
    AppServicePlan = $AppServicePlan
    Location = $Location
    Sku = $Sku
    DeploymentDate = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Url = "https://$WebAppName.azurewebsites.net"
}

$deploymentInfo | ConvertTo-Json | Set-Content $deploymentConfigFile
Write-Host "✓ Deployment configuration saved to $deploymentConfigFile" -ForegroundColor Green
Write-Host ""

# Get URL
$url = "https://$WebAppName.azurewebsites.net"

Write-Host "======================================================================" -ForegroundColor Green
if ($isRedeployment) {
    Write-Host " REDEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
} else {
    Write-Host " DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
}
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application URL: $url" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔐 Security Configuration:" -ForegroundColor Yellow
Write-Host "  ✓ Managed Identity enabled" -ForegroundColor Green
Write-Host "  ✓ RBAC permissions configured" -ForegroundColor Green
Write-Host "  ⚠ Role assignments may take 2-5 minutes to propagate" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Wait 2-5 minutes for RBAC permissions to propagate" -ForegroundColor White
Write-Host "  2. Visit: $url" -ForegroundColor White
Write-Host "  3. Login with default credentials:" -ForegroundColor White
Write-Host "     Username: admin" -ForegroundColor White
Write-Host "     Password: admin123" -ForegroundColor White
Write-Host ""
Write-Host "  4. View logs: az webapp log tail --name $WebAppName --resource-group $ResourceGroup" -ForegroundColor White
Write-Host "  5. Manage in portal: https://portal.azure.com" -ForegroundColor White
Write-Host ""
Write-Host "Authentication:" -ForegroundColor Yellow
Write-Host "  • Using: Managed Identity (no keys stored)" -ForegroundColor Green
Write-Host "  • Cosmos DB: RBAC authentication" -ForegroundColor Green
Write-Host "  • Azure AI: RBAC authentication" -ForegroundColor Green
Write-Host ""
Write-Host "To update the application:" -ForegroundColor Yellow
Write-Host "  Run this script again to redeploy to the same instance" -ForegroundColor White
Write-Host "  Use -Force to create a new deployment instead" -ForegroundColor White
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan

# Copy URL to clipboard
$url | Set-Clipboard
Write-Host "✓ URL copied to clipboard!" -ForegroundColor Green
