# Quick cleanup using Azure CLI directly
param(
    [string]$CosmosAccount = "zava-dev-cosmos-77cd5n",
    [string]$ResourceGroup = "RG-Zava-Backend-dev",
    [string]$Database = "logisticstracking"
)

Write-Host "🗑️  Cleaning up demo data from Cosmos DB..." -ForegroundColor Yellow
Write-Host "   Account: $CosmosAccount" -ForegroundColor Gray
Write-Host "   Database: $Database" -ForegroundColor Gray

# Get connection string
$connString = (az cosmosdb keys list --name $CosmosAccount --resource-group $ResourceGroup --type connection-strings | ConvertFrom-Json).connectionStrings | Where-Object {$_.description -eq 'Primary SQL Connection String'} | Select-Object -ExpandProperty connectionString

if (!$connString) {
    Write-Host "❌ Failed to get connection string"  -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Got connection string" -ForegroundColor Green

# Delete all parcels using Azure CLI
Write-Host "`n📋 Deleting parcels container..." -ForegroundColor Yellow
try {
    $null = az cosmosdb sql container delete `
        --account-name $CosmosAccount `
        --resource-group $ResourceGroup `
        --database-name $Database `
        --name "parcels" `
        --yes 2>$null
    
    Write-Host "   ✓ Parcels container deleted" -ForegroundColor Green
    
    # Recreate parcels container
    Write-Host "   Creating new parcels container..." -ForegroundColor Gray
    $null = az cosmosdb sql container create `
        --account-name $CosmosAccount `
        --resource-group $ResourceGroup `
        --database-name $Database `
        --name "parcels" `
        --partition-key-path "/store_location" 2>$null
    
    Write-Host "   ✓ Parcels container recreated" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Error with parcels: $_" -ForegroundColor Yellow
}

# Delete all manifests
Write-Host "`n📋 Deleting manifests container..." -ForegroundColor Yellow
try {
    $null = az cosmosdb sql container delete `
        --account-name $CosmosAccount `
        --resource-group $ResourceGroup `
        --database-name $Database `
        --name "Manifests" `
        --yes 2>$null
    
    Write-Host "   ✓ Manifests container deleted" -ForegroundColor Green
    
    # Recreate manifests container
    Write-Host "   Creating new manifests container..." -ForegroundColor Gray
    $null = az cosmosdb sql container create `
        --account-name $CosmosAccount `
        --resource-group $ResourceGroup `
        --database-name $Database `
        --name "Manifests" `
        --partition-key-path "/driver_id" 2>$null
    
    Write-Host "   ✓ Manifests container recreated" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Error with manifests: $_" -ForegroundColor Yellow
}

# Delete all approval requests
Write-Host "`n📋 Deleting approval_requests container..." -ForegroundColor Yellow
try {
    $null = az cosmosdb sql container delete `
        --account-name $CosmosAccount `
        --resource-group $ResourceGroup `
        --database-name $Database `
        --name "approval_requests" `
        --yes 2>$null
    
    Write-Host "   ✓ Approval requests container deleted" -ForegroundColor Green
    
    # Recreate approval_requests container
    Write-Host "   Creating new approval_requests container..." -ForegroundColor Gray
    $null = az cosmosdb sql container create `
        --account-name $CosmosAccount `
        --resource-group $ResourceGroup `
        --database-name $Database `
        --name "approval_requests" `
        --partition-key-path "/request_id" 2>$null
    
    Write-Host "   ✓ Approval requests container recreated" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Error with approval_requests: $_" -ForegroundColor Yellow
}

Write-Host "`n✨ Cleanup complete! Database ready for fresh data generation." -ForegroundColor Green
Write-Host "   Run: .\Scripts\populate_demo_data.ps1" -ForegroundColor Cyan
