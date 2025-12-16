# Setup RBAC Permissions for DT Logistics App Service Managed Identity
# This script grants all required Azure RBAC roles for the application to function properly

param(
    [Parameter(Mandatory=$false)]
    [string]$AppServiceName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "",
    
    [Parameter(Mandatory=$false)]
    [string]$CosmosAccountName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AIHubName = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔐 DT Logistics RBAC Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Auto-detect from deployment config if not provided
$deploymentConfigFile = "..\\.azure-deployment.json"
if (-not $AppServiceName -or -not $ResourceGroup) {
    if (Test-Path $deploymentConfigFile) {
        Write-Host "📋 Reading deployment configuration..." -ForegroundColor Yellow
        try {
            $deploymentConfig = Get-Content $deploymentConfigFile -Raw | ConvertFrom-Json
            
            if (-not $AppServiceName) {
                $AppServiceName = $deploymentConfig.WebAppName
                Write-Host "  ✓ App Service: $AppServiceName" -ForegroundColor Green
            }
            if (-not $ResourceGroup) {
                $ResourceGroup = $deploymentConfig.ResourceGroup
                Write-Host "  ✓ Resource Group: $ResourceGroup" -ForegroundColor Green
            }
        } catch {
            Write-Host "  ⚠ Could not read deployment config" -ForegroundColor Yellow
        }
        Write-Host ""
    }
}

# Auto-detect from .env if not provided
$envFile = "..\\.env"
if (-not $CosmosAccountName -or -not $AIHubName) {
    if (Test-Path $envFile) {
        Write-Host "📋 Reading .env configuration..." -ForegroundColor Yellow
        Get-Content $envFile | ForEach-Object {
            if (-not $CosmosAccountName -and $_ -match '^COSMOS_DB_ENDPOINT\\s*=\\s*"?https://([^.]+)\\.documents\\.azure\\.com') {
                $CosmosAccountName = $matches[1]
                Write-Host "  ✓ Cosmos DB: $CosmosAccountName" -ForegroundColor Green
            }
            if (-not $AIHubName -and $_ -match '^AZURE_VISION_ENDPOINT\\s*=\\s*"?https://([^.]+)\\.cognitiveservices\\.azure\\.com') {
                $AIHubName = $matches[1]
                Write-Host "  ✓ AI Hub: $AIHubName" -ForegroundColor Green
            }
            if (-not $AIHubName -and $_ -match '^AZURE_AI_PROJECT_ENDPOINT\\s*=\\s*"?https://([^.]+)\\.services\\.ai\\.azure\\.com') {
                $AIHubName = $matches[1]
                Write-Host "  ✓ AI Hub: $AIHubName" -ForegroundColor Green
            }
        }
        Write-Host ""
    }
}

# Validate required parameters
if (-not $AppServiceName -or -not $ResourceGroup) {
    Write-Host "❌ Error: Could not determine App Service name or Resource Group" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please provide parameters:" -ForegroundColor Yellow
    Write-Host "  .\setup_rbac_permissions.ps1 -AppServiceName <name> -ResourceGroup <rg>" -ForegroundColor White
    Write-Host ""
    Write-Host "Or ensure .azure-deployment.json exists in parent directory" -ForegroundColor Gray
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  App Service: $AppServiceName" -ForegroundColor White
Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor White
if ($CosmosAccountName) {
    Write-Host "  Cosmos DB: $CosmosAccountName" -ForegroundColor White
}
if ($AIHubName) {
    Write-Host "  AI Hub: $AIHubName" -ForegroundColor White
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get managed identity principal ID
Write-Host "📋 Retrieving managed identity..." -ForegroundColor Yellow
$principalId = az webapp identity show `
    --name $AppServiceName `
    --resource-group $ResourceGroup `
    --query principalId -o tsv

if (-not $principalId) {
    Write-Host "❌ Failed to retrieve managed identity. Ensure it's enabled:" -ForegroundColor Red
    Write-Host "   az webapp identity assign --name $AppServiceName --resource-group $ResourceGroup" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Managed Identity Principal ID: $principalId" -ForegroundColor Green
Write-Host ""

# Get subscription ID
$subscriptionId = az account show --query id -o tsv
Write-Host "📋 Subscription ID: $subscriptionId" -ForegroundColor Cyan
Write-Host ""

# 1. Cosmos DB Built-in Data Contributor
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1️⃣  Cosmos DB Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($CosmosAccountName) {
    Write-Host "Finding Cosmos DB account '$CosmosAccountName'..." -ForegroundColor Yellow
    $cosmosAccount = az cosmosdb list --query "[?name=='$CosmosAccountName'].{name:name, resourceGroup:resourceGroup}" -o json | ConvertFrom-Json
    
    if ($cosmosAccount -and $cosmosAccount.Count -gt 0) {
        $cosmosRG = $cosmosAccount[0].resourceGroup
        Write-Host "  ✓ Found in resource group: $cosmosRG" -ForegroundColor Green
        
        Write-Host "Granting 'Cosmos DB Built-in Data Contributor' role..." -ForegroundColor Yellow
        az cosmosdb sql role assignment create `
            --account-name $CosmosAccountName `
            --resource-group $cosmosRG `
            --role-definition-id "00000000-0000-0000-0000-000000000002" `
            --principal-id $principalId `
            --scope "/" 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Cosmos DB role assigned successfully" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Cosmos DB role assignment failed (may already exist)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Cosmos DB account '$CosmosAccountName' not found" -ForegroundColor Red
    }
} else {
    Write-Host "⊘ Cosmos DB account name not provided, skipping" -ForegroundColor Gray
}
Write-Host ""

# 2. Cognitive Services OpenAI Contributor
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "2️⃣  Azure AI Foundry - OpenAI Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "Granting 'Cognitive Services OpenAI Contributor' role..." -ForegroundColor Yellow
az role assignment create `
    --assignee-object-id $principalId `
    --assignee-principal-type ServicePrincipal `
    --role "Cognitive Services OpenAI Contributor" `
    --scope "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ OpenAI Contributor role assigned successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  OpenAI Contributor role assignment failed (may already exist)" -ForegroundColor Yellow
}
Write-Host ""

# 3. Azure AI Developer
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "3️⃣  Azure AI Foundry - Agents Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "Granting 'Azure AI Developer' role..." -ForegroundColor Yellow
az role assignment create `
    --assignee-object-id $principalId `
    --assignee-principal-type ServicePrincipal `
    --role "Azure AI Developer" `
    --scope "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Azure AI Developer role assigned successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Azure AI Developer role assignment failed (may already exist)" -ForegroundColor Yellow
}
Write-Host ""

# 4. Cognitive Services User (for read operations)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "4️⃣  Azure AI Foundry - Read Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "Granting 'Cognitive Services User' role..." -ForegroundColor Yellow
az role assignment create `
    --assignee-object-id $principalId `
    --assignee-principal-type ServicePrincipal `
    --role "Cognitive Services User" `
    --scope "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Cognitive Services User role assigned successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Cognitive Services User role assignment failed (may already exist)" -ForegroundColor Yellow
}
Write-Host ""

# 5. AI Hub Resource-Specific Permissions (CRITICAL)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "5️⃣  AI Hub Resource Permissions (agents/read)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($AIHubName) {
    Write-Host "Finding AI Hub '$AIHubName'..." -ForegroundColor Yellow
    $aiHub = az cognitiveservices account list --query "[?name=='$AIHubName'].{name:name, resourceGroup:resourceGroup}" -o json | ConvertFrom-Json
    
    if ($aiHub -and $aiHub.Count -gt 0) {
        $AIHubResourceGroup = $aiHub[0].resourceGroup
        Write-Host "  ✓ Found in resource group: $AIHubResourceGroup" -ForegroundColor Green
        
        $aiHubScope = "/subscriptions/$subscriptionId/resourceGroups/$AIHubResourceGroup/providers/Microsoft.CognitiveServices/accounts/$AIHubName"
        Write-Host "AI Hub Scope: $aiHubScope" -ForegroundColor Gray
        Write-Host ""

        Write-Host "Granting 'Cognitive Services Contributor' to AI Hub..." -ForegroundColor Yellow
        az role assignment create `
            --assignee-object-id $principalId `
            --assignee-principal-type ServicePrincipal `
            --role "Cognitive Services Contributor" `
            --scope $aiHubScope 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Cognitive Services Contributor assigned to AI Hub" -ForegroundColor Green
        } else {
            Write-Host "⚠️  AI Hub role assignment failed (may already exist)" -ForegroundColor Yellow
        }
        Write-Host ""

        Write-Host "Granting 'Azure AI Developer' to AI Hub..." -ForegroundColor Yellow
        az role assignment create `
            --assignee-object-id $principalId `
            --assignee-principal-type ServicePrincipal `
            --role "Azure AI Developer" `
            --scope $aiHubScope 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Azure AI Developer assigned to AI Hub" -ForegroundColor Green
        } else {
            Write-Host "⚠️  AI Hub role assignment failed (may already exist)" -ForegroundColor Yellow
        }
        Write-Host ""

        Write-Host "Granting 'Cognitive Services OpenAI Contributor' to AI Hub..." -ForegroundColor Yellow
        az role assignment create `
            --assignee-object-id $principalId `
            --assignee-principal-type ServicePrincipal `
            --role "Cognitive Services OpenAI Contributor" `
            --scope $aiHubScope 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Cognitive Services OpenAI Contributor assigned to AI Hub" -ForegroundColor Green
        } else {
            Write-Host "⚠️  AI Hub role assignment failed (may already exist)" -ForegroundColor Yellow
        }
        Write-Host ""

        Write-Host "Granting 'Cognitive Services OpenAI User' to AI Hub..." -ForegroundColor Yellow
        az role assignment create `
            --assignee-object-id $principalId `
            --assignee-principal-type ServicePrincipal `
            --role "Cognitive Services OpenAI User" `
            --scope $aiHubScope 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Cognitive Services OpenAI User assigned to AI Hub" -ForegroundColor Green
        } else {
            Write-Host "⚠️  AI Hub role assignment failed (may already exist)" -ForegroundColor Yellow
        }
        Write-Host ""

        Write-Host "Granting 'Cognitive Services Usages Reader' to AI Hub..." -ForegroundColor Yellow
        az role assignment create `
            --assignee-object-id $principalId `
            --assignee-principal-type ServicePrincipal `
            --role "Cognitive Services Usages Reader" `
            --scope $aiHubScope 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Cognitive Services Usages Reader assigned to AI Hub" -ForegroundColor Green
        } else {
            Write-Host "⚠️  AI Hub role assignment failed (may already exist)" -ForegroundColor Yellow
        }
        Write-Host ""
    } else {
        Write-Host "❌ AI Hub '$AIHubName' not found" -ForegroundColor Red
        Write-Host "⚠️  Skipping AI Hub-specific permissions" -ForegroundColor Yellow
        Write-Host ""
    }
} else {
    Write-Host "⊘ AI Hub name not provided, skipping" -ForegroundColor Gray
    Write-Host ""
}

# Verify role assignments
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "📋 Verifying Role Assignments" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "All role assignments for managed identity:" -ForegroundColor Yellow
az role assignment list `
    --assignee $principalId `
    --all `
    --query "[].{Role:roleDefinitionName, Scope:scope}" `
    --output table

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ RBAC Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  Important Notes:" -ForegroundColor Yellow
Write-Host "  • Role assignments can take up to 5 minutes to propagate" -ForegroundColor White
Write-Host "  • Restart the App Service to apply changes:" -ForegroundColor White
Write-Host "    az webapp restart --name $AppServiceName --resource-group $ResourceGroup" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Required Environment Variables:" -ForegroundColor Yellow
Write-Host "  • USE_MANAGED_IDENTITY=true" -ForegroundColor White
if ($CosmosAccountName) {
    Write-Host "  • COSMOS_DB_ENDPOINT=https://$CosmosAccountName.documents.azure.com:443/" -ForegroundColor White
}
Write-Host "  • Do NOT set COSMOS_CONNECTION_STRING or COSMOS_DB_KEY" -ForegroundColor Red
Write-Host ""
Write-Host "📋 Required Roles Granted:" -ForegroundColor Yellow
if ($CosmosAccountName) {
    Write-Host "  ✓ Cosmos DB Built-in Data Contributor (data plane access)" -ForegroundColor Green
}
Write-Host "  ✓ Cognitive Services OpenAI Contributor (OpenAI operations)" -ForegroundColor Green
Write-Host "  ✓ Azure AI Developer (agents/write permissions)" -ForegroundColor Green
Write-Host "  ✓ Cognitive Services User (agents/read permissions)" -ForegroundColor Green
if ($AIHubName) {
    Write-Host "  ✓ Cognitive Services Contributor (AI Hub - full access)" -ForegroundColor Green
    Write-Host "  ✓ Cognitive Services OpenAI User (agents/read data action)" -ForegroundColor Green
    Write-Host "  ✓ Cognitive Services Usages Reader (additional read permissions)" -ForegroundColor Green
}
Write-Host ""
Write-Host "⚠️  CRITICAL: AI Hub resource-specific roles are required for agents/read permission" -ForegroundColor Yellow
Write-Host ""
