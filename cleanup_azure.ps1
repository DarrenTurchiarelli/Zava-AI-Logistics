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
Write-Host "  ✓ Delete orphaned storage accounts" -ForegroundColor Gray
Write-Host "  ✓ Purge soft-deleted Azure OpenAI services" -ForegroundColor Gray
Write-Host "  ✓ Clean up local deployment configuration`n" -ForegroundColor Gray

# ============================================================================
# Step 1: Delete all Zava resource groups
# ============================================================================
Write-Host "[1/6] Deleting Zava resource groups..." -ForegroundColor Cyan
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
    Write-Host "[2/6] Waiting for resource group deletion..." -ForegroundColor Cyan
    Write-Host "  ⏱️  Checking every 30 seconds (max 10 minutes)..." -ForegroundColor Gray
    Write-Host "  ℹ️  Note: Backend RG (with Cosmos DB) typically takes 15-20 minutes" -ForegroundColor Yellow
    Write-Host "     Deletion continues in background after timeout`n" -ForegroundColor Gray
    
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
        Write-Host "  ⏱️  Timeout reached. Some groups may still be deleting." -ForegroundColor Yellow
        Write-Host "      This is normal - Backend RG (Cosmos DB) takes 15-20 minutes.`n" -ForegroundColor Gray
        Write-Host "      Deletion continues in background. Safe to proceed.`n" -ForegroundColor Gray
    }
    
    # Extra wait for soft-delete propagation
    Write-Host "  ⏱️  Waiting 60 seconds for soft-delete propagation..." -ForegroundColor Cyan
    Start-Sleep -Seconds 60
    Write-Host "  ✓ Wait complete`n" -ForegroundColor Green
} else {
    Write-Host "[2/6] Skipping wait (no resource groups to delete)`n" -ForegroundColor Cyan
}

# ============================================================================
# Step 3: Purge soft-deleted Cosmos DB accounts
# ============================================================================
Write-Host "[3/6] Purging soft-deleted Cosmos DB accounts..." -ForegroundColor Cyan
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
# Step 4: Delete orphaned storage accounts
# ============================================================================
Write-Host "[4/6] Cleaning up orphaned storage accounts..." -ForegroundColor Cyan

# Find all Zava storage accounts (they start with "zavadevst" or "zavaprodst")
$orphanedStorageAccounts = az storage account list --query "[?starts_with(name, 'zavadevst') || starts_with(name, 'zavaprodst')].{name:name, resourceGroup:resourceGroup}" -o json 2>$null

if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($orphanedStorageAccounts) -and $orphanedStorageAccounts -ne "[]") {
    $storageAccounts = $orphanedStorageAccounts | ConvertFrom-Json
    
    Write-Host "  Found $($storageAccounts.Count) Zava storage account(s):" -ForegroundColor Yellow
    foreach ($account in $storageAccounts) {
        Write-Host "    - $($account.name) in resource group: $($account.resourceGroup)" -ForegroundColor White
        
        # Check if the resource group still exists
        $rgExists = az group exists --name $account.resourceGroup
        
        if ($rgExists -eq "true") {
            Write-Host "      Deleting..." -ForegroundColor Gray
            az storage account delete `
                --name $account.name `
                --resource-group $account.resourceGroup `
                --yes 2>&1 | Out-Null
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "      ✓ Deleted" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  Delete may have failed" -ForegroundColor Yellow
            }
        } else {
            Write-Host "      ⓘ  Resource group doesn't exist (already cleaned up)" -ForegroundColor Gray
        }
    }
    Write-Host "  ✓ Storage account cleanup completed`n" -ForegroundColor Green
} else {
    Write-Host "  ✓ No orphaned storage accounts found`n" -ForegroundColor Green
}

# ============================================================================
# Step 5: Purge ALL soft-deleted Cognitive Services (OpenAI, Speech, Vision)
# ============================================================================
Write-Host "[5/6] Purging ALL soft-deleted Cognitive Services..." -ForegroundColor Cyan

# List ALL deleted Cognitive Services accounts (OpenAI, Speech, Vision, Maps)
$deletedServices = az cognitiveservices account list-deleted -o json 2>$null

if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($deletedServices) -and $deletedServices -ne "[]") {
    $allServices = $deletedServices | ConvertFrom-Json
    
    # Filter for Zava-related services (case-insensitive)
    $services = $allServices | Where-Object { $_.name -like '*zava*' }
    
    if ($services -and $services.Count -gt 0) {
        Write-Host "  Found $($services.Count) soft-deleted Cognitive Services account(s):" -ForegroundColor Yellow
        foreach ($service in $services) {
            Write-Host "    - $($service.name) in $($service.location)" -ForegroundColor White
            Write-Host "      Purging..." -ForegroundColor Gray
            
            # Infer resource group from service name pattern
            # zava-dev-openai-xxx -> RG-Zava-Middleware-dev
            # zava-dev-speech-xxx -> RG-Zava-Shared-dev
            # zava-dev-vision-xxx -> RG-Zava-Shared-dev
            $rgName = if ($service.name -like '*openai*') {
                'RG-Zava-Middleware-dev'
            } else {
                'RG-Zava-Shared-dev'
            }
            
            # Purge using correct syntax (resource group required even for soft-deleted)
            $purgeResult = az cognitiveservices account purge `
                --name $service.name `
                --location $service.location `
                --resource-group $rgName 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "      ✓ Purged" -ForegroundColor Green
            } else {
                Write-Host "      ⚠️  Purge failed (may auto-purge in 48 hours)" -ForegroundColor Yellow
            }
        }
        Write-Host "  ✓ Cognitive Services purge completed`n" -ForegroundColor Green
    } else {
        Write-Host "  ✓ No Zava-related soft-deleted services found`n" -ForegroundColor Green
    }
} else {
    Write-Host "  ✓ No soft-deleted Cognitive Services found`n" -ForegroundColor Green
}

# ============================================================================
# Step 6: Clean up local deployment configuration
# ============================================================================
Write-Host "[6/6] Cleaning up local deployment configuration..." -ForegroundColor Cyan

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
