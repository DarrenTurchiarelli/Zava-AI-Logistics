# =============================================================================
# generate_demo_data.ps1
# Standalone script to run generate_bulk_realistic_data.py against the live
# Azure Cosmos DB using your personal Azure CLI identity.
#
# Usage:
#   .\scripts\generate_demo_data.ps1
#   .\scripts\generate_demo_data.ps1 -CosmosAccountName <account-name>
#   .\scripts\generate_demo_data.ps1 -Count 500
#   .\scripts\generate_demo_data.ps1 -Count 100 -DemoOnly
#   .\scripts\generate_demo_data.ps1 -Count 2000 -SkipHighLoad
#
# Prerequisites:
#   az login (must be authenticated as darrent@microsoft.com)
#   pip install -e ".[dev]"  (or pip install -r requirements.txt)
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$CosmosAccountName = "",

    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "RG-Zava-Backend-dev",

    [Parameter(Mandatory=$false)]
    [string]$DatabaseName = "logisticstracking",

    [Parameter(Mandatory=$false)]
    [int]$Count = 2000,

    [Parameter(Mandatory=$false)]
    [switch]$DemoOnly,

    [Parameter(Mandatory=$false)]
    [switch]$SkipHighLoad,

    [Parameter(Mandatory=$false)]
    [switch]$SkipRbac
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Off
$projectRoot = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  Zava Demo Data Generator" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Verify Azure CLI login ────────────────────────────────────────────
Write-Host "[1/4] Checking Azure CLI authentication..." -ForegroundColor Yellow

$accountJson = az account show --output json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Not logged in. Run: az login" -ForegroundColor Red
    exit 1
}

$account = $accountJson | ConvertFrom-Json
$userEmail = $account.user.name
$tenantId  = $account.tenantId
$subId     = $account.id

Write-Host "  ✓ Logged in as : $userEmail" -ForegroundColor Green
Write-Host "  ✓ Subscription : $($account.name) ($subId)" -ForegroundColor Green
Write-Host "  ✓ Tenant       : $tenantId" -ForegroundColor Green
Write-Host ""

# Warn if wrong account
if ($userEmail -notlike "*microsoft.com*") {
    Write-Host "  ⚠  Expected a microsoft.com account. Current: $userEmail" -ForegroundColor Yellow
    $confirm = Read-Host "  Continue anyway? [y/N]"
    if ($confirm.Trim().ToLower() -ne 'y') { exit 1 }
}

# ── Step 2: Verify Cosmos DB account exists ───────────────────────────────────
Write-Host "[2/4] Verifying Cosmos DB account..." -ForegroundColor Yellow

if ([string]::IsNullOrWhiteSpace($CosmosAccountName)) {
    $cosmosListOutput = az cosmosdb list `
        --resource-group $ResourceGroup `
        --query "[].name" --output json 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Could not list Cosmos DB accounts in '$ResourceGroup'" -ForegroundColor Red
        Write-Host "    $cosmosListOutput" -ForegroundColor Yellow
        exit 1
    }

    $cosmosAccounts = @($cosmosListOutput | ConvertFrom-Json)
    if ($cosmosAccounts.Count -eq 0) {
        Write-Host "  ✗ No Cosmos DB account found in '$ResourceGroup'" -ForegroundColor Red
        Write-Host "    Check the -ResourceGroup parameter" -ForegroundColor Yellow
        exit 1
    }

    if ($cosmosAccounts.Count -eq 1) {
        $CosmosAccountName = $cosmosAccounts[0]
    } else {
        $deploymentConfigPath = Join-Path $projectRoot ".azure-deployment.json"
        $matchingAccounts = @()

        if (Test-Path $deploymentConfigPath) {
            $deploymentConfig = Get-Content $deploymentConfigPath -Raw | ConvertFrom-Json
            if ($deploymentConfig.AppServiceName -match '-([^-]+)$') {
                $deploymentSuffix = $Matches[1]
                $matchingAccounts = @($cosmosAccounts | Where-Object { $_ -like "*-$deploymentSuffix" })
            }
        }

        if ($matchingAccounts.Count -ne 1) {
            Write-Host "  ✗ Multiple Cosmos DB accounts found in '$ResourceGroup':" -ForegroundColor Red
            $cosmosAccounts | ForEach-Object {
                Write-Host "    - $_" -ForegroundColor Yellow
            }
            Write-Host "    Specify the intended account with -CosmosAccountName" -ForegroundColor Yellow
            exit 1
        }

        $CosmosAccountName = $matchingAccounts[0]
        Write-Host "  ✓ Matched current deployment: $CosmosAccountName" -ForegroundColor Green
    }
}

$cosmosCheck = az cosmosdb show `
    --name $CosmosAccountName `
    --resource-group $ResourceGroup `
    --query "documentEndpoint" --output tsv 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Cosmos DB account '$CosmosAccountName' not found in '$ResourceGroup'" -ForegroundColor Red
    Write-Host "    Check the -CosmosAccountName and -ResourceGroup parameters" -ForegroundColor Yellow
    exit 1
}

$cosmosEndpoint = $cosmosCheck.Trim()
Write-Host "  ✓ Cosmos DB : $CosmosAccountName" -ForegroundColor Green
Write-Host "  ✓ Endpoint  : $cosmosEndpoint" -ForegroundColor Green
Write-Host ""

# ── Step 3: Assign Cosmos DB Built-in Data Contributor to signed-in user ──────
# This is a Cosmos DB SQL *data-plane* role (not a standard Azure RBAC role).
# It allows reading/writing documents without needing an account key.
# Role definition ID: 00000000-0000-0000-0000-000000000002

if (-not $SkipRbac) {
    Write-Host "[3/4] Assigning Cosmos DB data-plane role to your identity..." -ForegroundColor Yellow

    # Get the Object ID of the signed-in user
    $userObjectId = az ad signed-in-user show --query id --output tsv 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $userObjectId) {
        Write-Host "  ✗ Could not retrieve your Azure AD Object ID." -ForegroundColor Red
        Write-Host "    Ensure you are logged in with a user account (not a service principal)." -ForegroundColor Yellow
        exit 1
    }
    $userObjectId = $userObjectId.Trim()
    Write-Host "  ✓ Your Object ID: $userObjectId" -ForegroundColor Green

    $cosmosScope = "/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.DocumentDB/databaseAccounts/$CosmosAccountName"
    $roleDefId   = "00000000-0000-0000-0000-000000000002"  # Built-in Data Contributor

    # Check if the user already has the role assigned
    $existingAssignments = az cosmosdb sql role assignment list `
        --account-name $CosmosAccountName `
        --resource-group $ResourceGroup `
        --output json 2>&1 | ConvertFrom-Json

    $alreadyAssigned = $existingAssignments | Where-Object {
        $_.properties.principalId -eq $userObjectId -and
        $_.properties.roleDefinitionId -like "*$roleDefId"
    }

    if ($alreadyAssigned) {
        Write-Host "  ✓ Role already assigned — skipping" -ForegroundColor Green
    } else {
        Write-Host "  Assigning Cosmos DB Built-in Data Contributor..." -ForegroundColor Gray
        $assignResult = az cosmosdb sql role assignment create `
            --account-name      $CosmosAccountName `
            --resource-group    $ResourceGroup `
            --role-definition-id "$cosmosScope/sqlRoleDefinitions/$roleDefId" `
            --principal-id      $userObjectId `
            --scope             $cosmosScope `
            --output none 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ✗ Role assignment failed: $assignResult" -ForegroundColor Red
            Write-Host ""
            Write-Host "  If you don't have permission to assign roles, ask an Owner/Contributor" -ForegroundColor Yellow
            Write-Host "  to run this once for your Object ID ($userObjectId):" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "    az cosmosdb sql role assignment create ``" -ForegroundColor Gray
            Write-Host "      --account-name $CosmosAccountName ``" -ForegroundColor Gray
            Write-Host "      --resource-group $ResourceGroup ``" -ForegroundColor Gray
            Write-Host "      --role-definition-id `"$cosmosScope/sqlRoleDefinitions/$roleDefId`" ``" -ForegroundColor Gray
            Write-Host "      --principal-id $userObjectId ``" -ForegroundColor Gray
            Write-Host "      --scope $cosmosScope" -ForegroundColor Gray
            Write-Host ""
            $continueAnyway = Read-Host "  Try to continue anyway (role may already exist)? [y/N]"
            if ($continueAnyway.Trim().ToLower() -ne 'y') { exit 1 }
        } else {
            Write-Host "  ✓ Role assigned" -ForegroundColor Green
            Write-Host "  ⏱  Waiting 15 seconds for RBAC to propagate..." -ForegroundColor Gray
            Start-Sleep -Seconds 15
        }
    }
    Write-Host ""
} else {
    Write-Host "[3/4] Skipping RBAC assignment (-SkipRbac flag)" -ForegroundColor Yellow
    Write-Host ""
}

# ── Step 4: Run the generator using AzureCliCredential ────────────────────────
Write-Host "[4/4] Running generate_bulk_realistic_data.py..." -ForegroundColor Yellow
Write-Host ""

# Set env vars so parcel_tracking_db.py uses AzureCliCredential (not key auth)
$env:COSMOS_DB_ENDPOINT       = $cosmosEndpoint
$env:COSMOS_DB_DATABASE_NAME  = $DatabaseName
$env:USE_MANAGED_IDENTITY     = "false"   # AzureCliCredential path in parcel_tracking_db.py
$env:COSMOS_DB_KEY            = ""        # Clear any stale key to force credential path
$env:COSMOS_CONNECTION_STRING = ""        # Clear connection string to avoid key-based fallback
$env:AZURE_TENANT_ID          = $tenantId # Ensure DefaultAzureCredential picks the right tenant

# Prefer the project virtual environment so generator dependencies are available.
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { $null }
if (-not $pythonExe) {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue)?.Source
}
if (-not $pythonExe) {
    $pythonExe = (Get-Command python3 -ErrorAction SilentlyContinue)?.Source
}
if (-not $pythonExe) {
    Write-Host "  ✗ Python not found. Activate your virtual environment first:" -ForegroundColor Red
    Write-Host "    .venv\Scripts\Activate.ps1" -ForegroundColor Gray
    exit 1
}
Write-Host "  ✓ Python: $pythonExe" -ForegroundColor Green
Write-Host ""

# Build generator args
$generatorArgs = @("utils/generators/generate_bulk_realistic_data.py")
if ($DemoOnly)    { $generatorArgs += "--demo-only" }
else              { $generatorArgs += "--count"; $generatorArgs += $Count }
if ($SkipHighLoad){ $generatorArgs += "--skip-high-load" }

Write-Host "  Command: python $($generatorArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

# Run from project root so relative imports resolve correctly
Push-Location $projectRoot
try {
    & $pythonExe @generatorArgs
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
    # Restore env vars
    Remove-Item Env:COSMOS_DB_KEY             -ErrorAction SilentlyContinue
    Remove-Item Env:COSMOS_CONNECTION_STRING  -ErrorAction SilentlyContinue
}

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host ("=" * 70) -ForegroundColor Green
    Write-Host "  ✅ Data generation complete!" -ForegroundColor Green
    Write-Host ("=" * 70) -ForegroundColor Green
} else {
    Write-Host ("=" * 70) -ForegroundColor Red
    Write-Host "  ✗ Generator exited with code $exitCode" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Troubleshooting tips:" -ForegroundColor Yellow
    Write-Host "    - Ensure virtual env is active: .venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "    - Re-run RBAC check: remove -SkipRbac flag" -ForegroundColor Gray
    Write-Host "    - Check Cosmos DB local auth is disabled (managed identity mode)" -ForegroundColor Gray
    Write-Host "    - Verify endpoint: az cosmosdb show --name $CosmosAccountName --resource-group $ResourceGroup --query documentEndpoint -o tsv" -ForegroundColor Gray
    Write-Host ("=" * 70) -ForegroundColor Red
    exit $exitCode
}
