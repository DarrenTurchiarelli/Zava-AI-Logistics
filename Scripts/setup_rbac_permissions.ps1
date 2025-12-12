# Setup RBAC Permissions for DT Logistics App Service Managed Identity
# This script grants all required Azure RBAC roles for the application to function properly

param(
    [Parameter(Mandatory=$true)]
    [string]$AppServiceName = "dt-logistics-web-8323",
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup = "dt-logistics-rg",
    
    [Parameter(Mandatory=$true)]
    [string]$CosmosAccountName = "logisticstracking"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔐 DT Logistics RBAC Setup" -ForegroundColor Cyan
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

Write-Host "Granting 'Cosmos DB Built-in Data Contributor' role..." -ForegroundColor Yellow
az cosmosdb sql role assignment create `
    --account-name $CosmosAccountName `
    --resource-group $ResourceGroup `
    --role-definition-id "00000000-0000-0000-0000-000000000002" `
    --principal-id $principalId `
    --scope "/"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Cosmos DB role assigned successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Cosmos DB role assignment failed (may already exist)" -ForegroundColor Yellow
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
Write-Host "  • COSMOS_DB_ENDPOINT=https://$CosmosAccountName.documents.azure.com:443/" -ForegroundColor White
Write-Host "  • Do NOT set COSMOS_CONNECTION_STRING or COSMOS_DB_KEY" -ForegroundColor Red
Write-Host ""
Write-Host "📋 Required Roles Granted:" -ForegroundColor Yellow
Write-Host "  ✓ Cosmos DB Built-in Data Contributor (data plane access)" -ForegroundColor Green
Write-Host "  ✓ Cognitive Services OpenAI Contributor (OpenAI operations)" -ForegroundColor Green
Write-Host "  ✓ Azure AI Developer (agents/write permissions)" -ForegroundColor Green
Write-Host "  ✓ Cognitive Services User (agents/read permissions)" -ForegroundColor Green
Write-Host ""
