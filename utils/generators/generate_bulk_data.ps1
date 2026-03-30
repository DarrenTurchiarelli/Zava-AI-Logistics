#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate bulk realistic test data for Zava Logistics
.DESCRIPTION
    Temporarily enables Cosmos DB local auth, generates synthetic parcel data, then re-secures the database.
    No full deployment required.
.PARAMETER ParcelCount
    Number of parcels to generate (default: 2000)
.PARAMETER CosmosAccount
    Cosmos DB account name (auto-detected from .azure-deployment.json if available)
.PARAMETER ResourceGroup
    Resource group name (auto-detected from .azure-deployment.json if available)
.EXAMPLE
    .\utils\generators\generate_bulk_data.ps1
    .\utils\generators\generate_bulk_data.ps1 -ParcelCount 5000
#>

param(
    [int]$ParcelCount = 2000,
    [string]$CosmosAccount = "",
    [string]$ResourceGroup = ""
)

$ErrorActionPreference = "Stop"

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         BULK DATA GENERATOR FOR ZAVA LOGISTICS                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Auto-detect deployment info if available
if ([string]::IsNullOrEmpty($ResourceGroup)) {
    # Look for deployment config in both current dir and root (../../)
    $configPath = if (Test-Path ".azure-deployment.json") { ".azure-deployment.json" } 
                  elseif (Test-Path "../../.azure-deployment.json") { "../../.azure-deployment.json" }
                  else { $null }
    
    if ($configPath) {
        Write-Host "📋 Detecting existing deployment..." -ForegroundColor Cyan
        $deploymentInfo = Get-Content $configPath | ConvertFrom-Json
        $ResourceGroup = $deploymentInfo.BackendResourceGroup
        Write-Host "✓ Found resource group: $ResourceGroup" -ForegroundColor Green
    } else {
        Write-Host "❌ No deployment found. Please provide -ResourceGroup parameter" -ForegroundColor Red
        Write-Host "   Or run deploy_to_azure.ps1 first to create the infrastructure`n" -ForegroundColor Yellow
        exit 1
    }
}

# Auto-detect Cosmos DB account in the resource group
if ([string]::IsNullOrEmpty($CosmosAccount)) {
    Write-Host "🔍 Finding Cosmos DB account in $ResourceGroup..." -ForegroundColor Cyan
    $cosmosAccounts = az cosmosdb list --resource-group $ResourceGroup --query "[].name" -o tsv
    
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($cosmosAccounts)) {
        Write-Host "❌ No Cosmos DB account found in $ResourceGroup" -ForegroundColor Red
        Write-Host "   Please provide -CosmosAccount parameter`n" -ForegroundColor Yellow
        exit 1
    }
    
    $cosmosAccountsArray = @($cosmosAccounts -split "`n" | Where-Object { $_.Trim() -ne "" })
    if ($cosmosAccountsArray.Count -gt 1) {
        Write-Host "⚠️  Multiple Cosmos DB accounts found. Using first: $($cosmosAccountsArray[0])" -ForegroundColor Yellow
    }
    
    $CosmosAccount = $cosmosAccountsArray[0]
    Write-Host "✓ Found Cosmos DB account: $CosmosAccount`n" -ForegroundColor Green
}

# Verify Azure CLI is logged in
Write-Host "🔐 Checking Azure authentication..." -ForegroundColor Cyan
$azAccount = az account show 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Not logged in to Azure. Please run: az login`n" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Azure authenticated`n" -ForegroundColor Green

# Step 1: Temporarily enable Cosmos DB local auth
Write-Host "🔓 Step 1/5: Enabling Cosmos DB local authentication..." -ForegroundColor Cyan
$cosmosResourceId = "/subscriptions/$((az account show --query id -o tsv))/resourceGroups/$ResourceGroup/providers/Microsoft.DocumentDB/databaseAccounts/$CosmosAccount"
az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=false --output none

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to enable local auth. Check your permissions.`n" -ForegroundColor Red
    exit 1
}

# Verify local auth was enabled
$localAuthStatus = az cosmosdb show --name $CosmosAccount --resource-group $ResourceGroup --query "disableLocalAuth" -o tsv
if ($localAuthStatus -eq "true") {
    Write-Host "⚠️  Warning: Local auth still shows as disabled. Waiting for propagation..." -ForegroundColor Yellow
} else {
    Write-Host "✓ Local auth enabled (verified)" -ForegroundColor Green
}

# Step 2: Get connection string
Write-Host "`n🔑 Step 2/5: Getting connection string..." -ForegroundColor Cyan
$connStr = az cosmosdb keys list --name $CosmosAccount --resource-group $ResourceGroup --type connection-strings --query "connectionStrings[0].connectionString" -o tsv

if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($connStr)) {
    Write-Host "❌ Failed to get connection string`n" -ForegroundColor Red
    # Try to re-secure before exiting
    az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --output none
    exit 1
}

$env:COSMOS_CONNECTION_STRING = $connStr
$env:FORCE_KEY_AUTH = "true"  # Don't fall back to Azure AD - we explicitly want key-based auth
Write-Host "✓ Connection string configured" -ForegroundColor Green

# Step 3: Wait for auth propagation
Write-Host "`n⏱  Step 3/5: Waiting 90 seconds for auth changes to propagate..." -ForegroundColor Yellow
Write-Host "   (Cosmos DB auth changes can take 60-90 seconds to fully propagate)" -ForegroundColor Gray
Start-Sleep -Seconds 90

# Step 4: Generate data
Write-Host "`n📦 Step 4/5: Generating $ParcelCount parcels..." -ForegroundColor Cyan
Write-Host "   This will take approximately $([math]::Ceiling($ParcelCount / 400)) to $([math]::Ceiling($ParcelCount / 200)) minutes`n" -ForegroundColor Yellow

$generateArgs = @()
if ($ParcelCount -ne 2000) {
    $generateArgs += "--count", $ParcelCount.ToString()
}

# Determine script path (works from root or utils/generators)
$scriptPath = if (Test-Path "utils/generators/generate_bulk_realistic_data.py") {
    "utils/generators/generate_bulk_realistic_data.py"
} elseif (Test-Path "generate_bulk_realistic_data.py") {
    "generate_bulk_realistic_data.py"
} else {
    Write-Host "❌ Cannot find generate_bulk_realistic_data.py" -ForegroundColor Red
    Write-Host "   Run from project root or utils/generators folder`n" -ForegroundColor Yellow
    # Re-secure before exiting
    az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --output none
    exit 1
}

try {
    & python $scriptPath @generateArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n❌ Data generation failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
        $generationSuccess = $false
    } else {
        Write-Host "`n✓ Data generation completed successfully!" -ForegroundColor Green
        $generationSuccess = $true
    }
} catch {
    Write-Host "`n❌ Data generation failed: $_" -ForegroundColor Red
    $generationSuccess = $false
}

# Step 5: Re-secure Cosmos DB (always do this, even if generation failed)
Write-Host "`n🔒 Step 5/5: Re-securing Cosmos DB (disabling local auth)..." -ForegroundColor Cyan
az resource update --ids $cosmosResourceId --set properties.disableLocalAuth=true --output none

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Failed to re-secure Cosmos DB. Please manually disable local auth in Azure Portal." -ForegroundColor Yellow
} else {
    Write-Host "✓ Cosmos DB secured (local auth disabled)" -ForegroundColor Green
}

# Clean up environment variables
Remove-Item Env:\COSMOS_CONNECTION_STRING -ErrorAction SilentlyContinue
Remove-Item Env:\FORCE_KEY_AUTH -ErrorAction SilentlyContinue

# Final summary
Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
if ($generationSuccess) {
    Write-Host "║                    ✓ GENERATION COMPLETE                       ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
    Write-Host "✅ Successfully generated $ParcelCount parcels" -ForegroundColor Green
    Write-Host "   • Demo parcels: RG857954, DT202512170037" -ForegroundColor White
    Write-Host "   • Distributed across all Australian states" -ForegroundColor White
    Write-Host "   • Full event histories and photos included" -ForegroundColor White
    Write-Host "   • Driver manifests populated`n" -ForegroundColor White
} else {
    Write-Host "║                    ❌ GENERATION FAILED                         ║" -ForegroundColor Red
    Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
    Write-Host "Database has been re-secured, but data generation did not complete." -ForegroundColor Yellow
    Write-Host "Check the error messages above for details.`n" -ForegroundColor Yellow
    exit 1
}
