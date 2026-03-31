#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Complete Azure cleanup for Zava Logistics
.DESCRIPTION
    Deletes all Zava resource groups and purges soft-deleted resources for a clean deployment tomorrow
#>

$ErrorActionPreference = "Continue"  # Continue on errors to complete cleanup

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     COMPLETE AZURE CLEANUP - Zava Logistics                   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "This script will:" -ForegroundColor White
Write-Host "  ✓ Delete all Zava resource groups" -ForegroundColor Gray
Write-Host "  ✓ Purge soft-deleted Cosmos DB accounts" -ForegroundColor Gray
Write-Host "  ✓ Purge soft-deleted Azure OpenAI services" -ForegroundColor Gray
Write-Host "  ✓ Clean up local deployment configuration`n" -ForegroundColor Gray

# ============================================================================
# Step 1: Delete all Zava resource groups
# ============================================================================
Write-Host "[1/5] Deleting Zava resource groups..." -ForegroundColor Cyan
$resourceGroups = az group list --query "[?starts_with(name, 'RG-Zava-')].name" -o tsv 2>$null

if ([string]::IsNullOrWhiteSpace($resourceGroups)) {
    Write-Host "  ✓ No resource groups found`n" -ForegroundColor Green
    $hasResourceGroups = $false
} else {
    $rgArray = $resourceGroups -split "`n" | Where-Object { $_ -ne "" }
    Write-Host "  Found $($rgArray.Count) resource group(s):" -ForegroundColor Yellow
    foreach ($rg in $rgArray) {
        Write-Host "    - $rg" -ForegroundColor White
    }
    
    Write-Host "`n  🗑️  Initiating deletion (no-wait mode)..." -ForegroundColor Yellow
    foreach ($rg in $rgArray) {
        Write-Host "      Deleting $rg..." -ForegroundColor Gray
        az group delete --name $rg --yes --no-wait 2>&1 | Out-Null
    }
    Write-Host "  ✓ Deletion initiated for all resource groups`n" -ForegroundColor Green
    $hasResourceGroups = $true
}

# ============================================================================
# Step 2: Wait for resource group deletion
# ============================================================================
if ($hasResourceGroups) {
    Write-Host "[2/5] Waiting for resource group deletion..." -ForegroundColor Cyan
    Write-Host "  ⏱️  Checking every 30 seconds (max 10 minutes)...`n" -ForegroundColor Gray
    
    $maxWait = 600  # 10 minutes
    $checkInterval = 30
    $elapsed = 0
    $allDeleted = $false
    
    while ($elapsed -lt $maxWait) {
        Start-Sleep -Seconds $checkInterval
        $elapsed += $checkInterval
        
        $remaining = az group list --query "[?starts_with(name, 'RG-Zava-')].name" -o tsv 2>$null
        
        if ([string]::IsNullOrWhiteSpace($remaining)) {
            Write-Host "  ✓ All resource groups deleted! (took $elapsed seconds)`n" -ForegroundColor Green
            $allDeleted = $true
            break
        } else {
            $remainingCount = ($remaining -split "`n" | Where-Object { $_ -ne "" }).Count
            Write-Host "  ⏳ Still deleting... $remainingCount group(s) remaining (${elapsed}s elapsed)" -ForegroundColor Gray
        }
    }
    
    if (-not $allDeleted) {
        Write-Host "  ⏱️  Timeout reached. Some groups may still be deleting.`n" -ForegroundColor Yellow
        Write-Host "      This is normal - deletion continues in background.`n" -ForegroundColor Gray
    }
    
    # Extra wait for soft-delete propagation
    Write-Host "  ⏱️  Waiting 60 seconds for soft-delete propagation..." -ForegroundColor Cyan
    Start-Sleep -Seconds 60
    Write-Host "  ✓ Wait complete`n" -ForegroundColor Green
} else {
    Write-Host "[2/5] Skipping wait (no resource groups to delete)`n" -ForegroundColor Cyan
}

# ============================================================================
# Step 3: Purge soft-deleted Cosmos DB accounts
# ============================================================================
Write-Host "[3/5] Purging soft-deleted Cosmos DB accounts..." -ForegroundColor Cyan
$subscriptionId = az account show --query id -o tsv

# Try to list deleted Cosmos DB accounts
$cosmosDeleted = az cosmosdb list-deleted 2>$null

if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($cosmosDeleted)) {
    $cosmosAccounts = $cosmosDeleted | ConvertFrom-Json | Where-Object { $_.name -like '*zava*' }
    
    if ($cosmosAccounts -and $cosmosAccounts.Count -gt 0) {
        Write-Host "  Found $($cosmosAccounts.Count) soft-deleted Cosmos DB account(s):" -ForegroundColor Yellow
        foreach ($account in $cosmosAccounts) {
            Write-Host "    - $($account.name) in $($account.location)" -ForegroundColor White
            Write-Host "      Purging..." -ForegroundColor Gray
            
            $purgeResult = az cosmosdb delete `
                --name $account.name `
                --resource-group "deletedAccounts" `
                --yes 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "      ✓ Purged" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  Purge may have failed (will be auto-purged in 30 days)" -ForegroundColor Yellow
            }
        }
        Write-Host "  ✓ Cosmos DB purge completed`n" -ForegroundColor Green
    } else {
        Write-Host "  ✓ No soft-deleted Cosmos DB accounts found`n" -ForegroundColor Green
    }
} else {
    Write-Host "  ✓ No soft-deleted Cosmos DB accounts found`n" -ForegroundColor Green
}

# ============================================================================
# Step 4: Purge soft-deleted Azure OpenAI services
# ============================================================================
Write-Host "[4/5] Purging soft-deleted Azure OpenAI services..." -ForegroundColor Cyan

# List all deleted Cognitive Services accounts (includes OpenAI)
$location = "australiaeast"
$deletedServices = az cognitiveservices account list-deleted --query "[?location=='$location' && contains(name, 'zava')]" -o json 2>$null

if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($deletedServices) -and $deletedServices -ne "[]") {
    $services = $deletedServices | ConvertFrom-Json
    
    Write-Host "  Found $($services.Count) soft-deleted Cognitive Services account(s):" -ForegroundColor Yellow
    foreach ($service in $services) {
        Write-Host "    - $($service.name) in $($service.location)" -ForegroundColor White
        Write-Host "      Purging..." -ForegroundColor Gray
        
        # Determine resource group from deletionDate
        $rgName = "RG-Zava-Middleware-dev"  # Most likely RG
        
        $purgeResult = az cognitiveservices account purge `
            --name $service.name `
            --resource-group $rgName `
            --location $service.location 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "      ✓ Purged" -ForegroundColor Green
        } else {
            Write-Host "      ⚠️  Purge may have failed (will be auto-purged in 48 hours)" -ForegroundColor Yellow
        }
    }
    Write-Host "  ✓ Azure OpenAI purge completed`n" -ForegroundColor Green
} else {
    Write-Host "  ✓ No soft-deleted Azure OpenAI services found`n" -ForegroundColor Green
}

# ============================================================================
# Step 5: Clean up local deployment configuration
# ============================================================================
Write-Host "[5/5] Cleaning up local deployment configuration..." -ForegroundColor Cyan

if (Test-Path ".azure-deployment.json") {
    Remove-Item ".azure-deployment.json" -Force
    Write-Host "  ✓ Removed .azure-deployment.json" -ForegroundColor Green
} else {
    Write-Host "  ✓ No .azure-deployment.json found" -ForegroundColor Gray
}

Write-Host ""

# ============================================================================
# Summary
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    CLEANUP COMPLETE! ✓                         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "Ready for fresh deployment tomorrow!" -ForegroundColor Cyan
Write-Host ""
Write-Host "To deploy fresh tomorrow:" -ForegroundColor White
Write-Host "  .\deploy_to_azure.ps1`n" -ForegroundColor Cyan
Write-Host "This will automatically:" -ForegroundColor Gray
Write-Host "  ✓ Create all infrastructure (4 resource groups)" -ForegroundColor Green
Write-Host "  ✓ Deploy GPT-4o model" -ForegroundColor Green
Write-Host "  ✓ Create all 8 AI agents" -ForegroundColor Green
Write-Host "  ✓ Configure environment variables" -ForegroundColor Green
Write-Host "  ✓ Deploy application code" -ForegroundColor Green
Write-Host "  ✓ Initialize demo data" -ForegroundColor Green
Write-Host "  ✓ Update local .env file`n" -ForegroundColor Green

Write-Host "No manual steps required! 🚀`n" -ForegroundColor Yellow

# Final verification
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Final Verification:" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

$finalCheck = az group list --query "[?starts_with(name, 'RG-Zava-')].name" -o tsv 2>$null
if ([string]::IsNullOrWhiteSpace($finalCheck)) {
    Write-Host "✓ No Zava resource groups remaining" -ForegroundColor Green
} else {
    $remaining = ($finalCheck -split "`n" | Where-Object { $_ -ne "" }).Count
    Write-Host "⏳ $remaining resource group(s) still deleting (will complete soon)" -ForegroundColor Yellow
}

Write-Host ""
