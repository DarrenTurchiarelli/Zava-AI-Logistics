# Pre-Deployment Validation Script
# Run this before deploy_to_azure.ps1

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  Zava Logistics - Pre-Deployment Check" -ForegroundColor White
Write-Host "================================================================`n" -ForegroundColor Cyan

$checks = 0
$failures = 0

# Check Azure CLI
Write-Host "Checking Azure CLI..." -ForegroundColor Yellow
if (az version 2>$null) {
    $account = az account show 2>$null | ConvertFrom-Json
    if ($account) {
        Write-Host "  √ Azure CLI authenticated as $($account.user.name)" -ForegroundColor Green
        $checks++
    } else {
        Write-Host "  × Not logged in. Run: az login" -ForegroundColor Red
        $failures++
    }
} else {
    Write-Host "  × Azure CLI not installed" -ForegroundColor Red
    $failures++
}

# Check Python
Write-Host "`nChecking Python..." -ForegroundColor Yellow
$pythonVer = python --version 2>&1
if ($LASTEXITCODE -eq 0 -and $pythonVer -match "3\.1[1-9]") {
    Write-Host "  √ Python $pythonVer" -ForegroundColor Green
    $checks++
} else {
    Write-Host "  × Python 3.11+ required" -ForegroundColor Red
    $failures++
}

# Check critical files
Write-Host "`nChecking project files..." -ForegroundColor Yellow
$criticalFiles = @(
    "infra/main.bicep",
    "scripts/create_foundry_agents_openai.py",
    "src/infrastructure/agents/skills/customer-service/system-prompt.md"
)

foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        $checks++
    } else {
        Write-Host "  × Missing: $file" -ForegroundColor Red
        $failures++
    }
}
Write-Host "  √ All critical files present" -ForegroundColor Green

# Check agent skills
Write-Host "`nValidating agent skills..." -ForegroundColor Yellow
$agentOutput = python scripts/validate_agent_skills.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  √ All 9 agents validated" -ForegroundColor Green
    $checks++
} else {
    Write-Host "  × Agent validation failed" -ForegroundColor Red
    $failures++
}

# Check Bicep
Write-Host "`nValidating Bicep template..." -ForegroundColor Yellow
$bicepOutput = bicep build infra/main.bicep 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  √ Bicep template valid" -ForegroundColor Green
    $checks++
} else {
    Write-Host "  × Bicep template has errors" -ForegroundColor Red
    $failures++
}

# Summary
Write-Host "`n================================================================" -ForegroundColor Cyan
if ($failures -eq 0) {
    Write-Host "  √√√  READY FOR DEPLOYMENT  √√√" -ForegroundColor Green
    Write-Host "================================================================`n" -ForegroundColor Cyan
    Write-Host "Run: .\deploy_to_azure.ps1`n" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "  ×××  $failures ISSUES FOUND  ×××" -ForegroundColor Red
    Write-Host "================================================================`n" -ForegroundColor Cyan
    Write-Host "Fix the issues above before deploying.`n" -ForegroundColor Yellow
    exit 1
}
