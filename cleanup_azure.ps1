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
Write-Host "  ✓ Purge soft-deleted Azure OpenAI / Cognitive Services" -ForegroundColor Gray
Write-Host "  ✓ Clean up local deployment configuration`n" -ForegroundColor Gray

# ============================================================================
# Helper: attempt one Cosmos DB purge sweep — returns count of accounts purged
# ============================================================================
function Invoke-CosmosPurgeSweep {
    $deleted = az cosmosdb list-deleted -o json 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($deleted)) { return 0 }

    $accounts = $deleted | ConvertFrom-Json | Where-Object { $_.name -like '*zava*' }
    if (-not $accounts -or $accounts.Count -eq 0) { return 0 }

    $purged = 0
    foreach ($acct in $accounts) {
        Write-Host "    🗑️  Purging Cosmos DB: $($acct.name) ($($acct.location))..." -ForegroundColor Yellow
        az cosmosdb delete --name $acct.name --resource-group "deletedAccounts" --yes 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "       ✓ Purged" -ForegroundColor Green
            $purged++
        } else {
            Write-Host "       ⚠️  Purge failed (auto-purges in 30 days)" -ForegroundColor Yellow
        }
    }
    return $purged
}

# ============================================================================
# Helper: attempt one Cognitive Services purge sweep — returns count purged
# ============================================================================
function Invoke-CogServicesPurgeSweep {
    $deleted = az cognitiveservices account list-deleted -o json 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($deleted) -or $deleted -eq "[]") { return 0 }

    $services = $deleted | ConvertFrom-Json | Where-Object { $_.name -like '*zava*' }
    if (-not $services -or $services.Count -eq 0) { return 0 }

    $purged = 0
    foreach ($svc in $services) {
        $rgName = if ($svc.name -like '*openai*') { 'RG-Zava-Middleware-dev' } else { 'RG-Zava-Shared-dev' }
        Write-Host "    🗑️  Purging Cognitive Service: $($svc.name) ($($svc.location))..." -ForegroundColor Yellow
        az cognitiveservices account purge `
            --name $svc.name `
            --location $svc.location `
            --resource-group $rgName 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "       ✓ Purged" -ForegroundColor Green
            $purged++
        } else {
            Write-Host "       ⚠️  Purge failed (auto-purges in 48 hours)" -ForegroundColor Yellow
        }
    }
    return $purged
}

# ============================================================================
# Step 1: Fire all RG deletions immediately (no-wait), then clean local files
# ============================================================================
Write-Host "[1/3] Firing resource group deletions..." -ForegroundColor Cyan
$resourceGroups = az group list --query "[?starts_with(name, 'RG-Zava-')].name" -o tsv 2>$null

$hasResourceGroups = $false
if ([string]::IsNullOrWhiteSpace($resourceGroups)) {
    Write-Host "  ✓ No resource groups found`n" -ForegroundColor Green
} else {
    $rgArray = $resourceGroups -split "`n" | Where-Object { $_ -ne "" }
    Write-Host "  Found $($rgArray.Count) resource group(s) — firing deletions in parallel:" -ForegroundColor Yellow
    foreach ($rg in $rgArray) {
        Write-Host "    🗑️  $rg" -ForegroundColor Gray
        az group delete --name $rg --yes --no-wait 2>&1 | Out-Null
    }
    Write-Host "  ✓ All deletions fired — continuing without blocking`n" -ForegroundColor Green
    $hasResourceGroups = $true
}

# ============================================================================
# Step 2: Clean local config immediately — no Azure dependency
# ============================================================================
Write-Host "[2/3] Cleaning up local deployment configuration..." -ForegroundColor Cyan
if (Test-Path ".azure-deployment.json") {
    Remove-Item ".azure-deployment.json" -Force
    Write-Host "  ✓ Removed .azure-deployment.json" -ForegroundColor Green
} else {
    Write-Host "  ✓ No .azure-deployment.json found" -ForegroundColor Gray
}
Write-Host ""

# ============================================================================
# Step 3: Combined poll loop — check RG deletion + purge soft-deleted resources
#
# Resources enter soft-delete state DURING RG deletion (not after), so purge
# attempts start as soon as they appear — no need to wait for full RG deletion.
# Each 30-second iteration checks RG status AND sweeps both purge lists.
# ============================================================================
if ($hasResourceGroups) {
    Write-Host "[3/3] Monitoring deletion + purging soft-deleted resources..." -ForegroundColor Cyan
    Write-Host "  ℹ️  Purges run every 30s as resources enter soft-delete state" -ForegroundColor Gray
    Write-Host "  ℹ️  Backend RG (Cosmos DB) typically takes 15-20 min — script exits early if done`n" -ForegroundColor Gray

    $maxWait      = 1200  # 20 minutes maximum
    $checkInterval = 30
    $elapsed       = 0
    $rgsDone       = $false
    $cosmosDone    = $false
    $cogSvcsDone   = $false

    while ($elapsed -lt $maxWait) {
        Start-Sleep -Seconds $checkInterval
        $elapsed += $checkInterval

        # ── Check remaining resource groups ─────────────────────────────────
        $remaining = az group list --query "[?starts_with(name, 'RG-Zava-')].name" -o tsv 2>$null
        if ([string]::IsNullOrWhiteSpace($remaining)) {
            if (-not $rgsDone) {
                Write-Host "  ✅ All resource groups deleted (${elapsed}s)" -ForegroundColor Green
                $rgsDone = $true
            }
        } else {
            $count = ($remaining -split "`n" | Where-Object { $_ -ne "" }).Count
            Write-Host "  ⏳ ${elapsed}s — $count RG(s) still deleting..." -ForegroundColor Gray
        }

        # ── Opportunistic Cosmos DB purge ────────────────────────────────────
        if (-not $cosmosDone) {
            $purged = Invoke-CosmosPurgeSweep
            if ($purged -gt 0) {
                Write-Host "  ✅ Cosmos DB: $purged account(s) purged" -ForegroundColor Green
            }
            # Mark done once RGs are gone and a clean sweep confirms nothing left
            if ($rgsDone) {
                $check = az cosmosdb list-deleted -o json 2>$null
                $remaining_cosmos = if ($check) { $check | ConvertFrom-Json | Where-Object { $_.name -like '*zava*' } } else { @() }
                if (-not $remaining_cosmos -or $remaining_cosmos.Count -eq 0) { $cosmosDone = $true }
            }
        }

        # ── Opportunistic Cognitive Services purge ───────────────────────────
        if (-not $cogSvcsDone) {
            $purged = Invoke-CogServicesPurgeSweep
            if ($purged -gt 0) {
                Write-Host "  ✅ Cognitive Services: $purged service(s) purged" -ForegroundColor Green
            }
            if ($rgsDone) {
                $check = az cognitiveservices account list-deleted -o json 2>$null
                $remaining_cog = if ($check -and $check -ne "[]") { $check | ConvertFrom-Json | Where-Object { $_.name -like '*zava*' } } else { @() }
                if (-not $remaining_cog -or $remaining_cog.Count -eq 0) { $cogSvcsDone = $true }
            }
        }

        # ── Exit early once everything is confirmed clean ────────────────────
        if ($rgsDone -and $cosmosDone -and $cogSvcsDone) {
            Write-Host ""
            Write-Host "  ✅ All resource groups deleted and soft-deleted resources purged`n" -ForegroundColor Green
            break
        }
    }

    if ($elapsed -ge $maxWait) {
        Write-Host ""
        Write-Host "  ⏱️  Max wait reached — remaining deletions continue in the background." -ForegroundColor Yellow
        Write-Host "      Re-run this script before deploying if you see soft-delete conflicts.`n" -ForegroundColor Gray
    }
} else {
    Write-Host "[3/3] Checking for any leftover soft-deleted resources..." -ForegroundColor Cyan
    Invoke-CosmosPurgeSweep    | Out-Null
    Invoke-CogServicesPurgeSweep | Out-Null
    Write-Host "  ✓ Done`n" -ForegroundColor Green
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
