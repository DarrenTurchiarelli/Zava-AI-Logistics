# =============================================================================
# Deploy Code Only - Quick Fix for Existing Infrastructure
# =============================================================================
# Use this to deploy application code to existing Azure infrastructure
# without redeploying everything.
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$WebAppName = "zava-dev-web-zjypho",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "RG-Zava-Frontend-dev"
)

Write-Host "`n" -NoNewline
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host " Deploy Application Code Only" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

Write-Host "Target: $WebAppName" -ForegroundColor Yellow
Write-Host "Resource Group: $ResourceGroup" -ForegroundColor Yellow
Write-Host ""

# Step 1: Create deployment package
Write-Host "[1/4] Creating deployment package..." -ForegroundColor Cyan

$tempZip = "$env:TEMP\zava-deploy-$(Get-Date -Format 'yyyyMMddHHmmss').zip"

# Exclusion patterns
$excludePatterns = @(
    "*.git*", ".github", ".vscode", ".azure", ".deployment.json",
    "*__pycache__*", "*.pyc", "*.pyo", "*.pyd",
    ".env", ".env.*", "*.log",
    "node_modules", ".venv", "venv", "env",
    "*.zip", "deploy*.zip",
    ".vs", "*.suo", "*.user",
    "tests", "*test*.py", "Scripts/test*.py",
    "deploy_code_only.ps1"
)

# Get production files only
$files = Get-ChildItem -Recurse -File | Where-Object {
    $file = $_
    $shouldInclude = $true
    foreach ($pattern in $excludePatterns) {
        if ($file.FullName -like "*$pattern*") {
            $shouldInclude = $false
            break
        }
    }
    $shouldInclude
}

Write-Host "  Including $($files.Count) files..." -ForegroundColor Gray
$files | Compress-Archive -DestinationPath $tempZip -Force

$zipSize = [math]::Round((Get-Item $tempZip).Length / 1MB, 2)
Write-Host "  ✓ Package created: $zipSize MB" -ForegroundColor Green
Write-Host ""

# Step 2: Deploy to Azure
Write-Host "[2/4] Deploying to Azure..." -ForegroundColor Cyan
Write-Host "  This will take 2-4 minutes (Oryx build)..." -ForegroundColor Gray
Write-Host ""

$deployOutput = az webapp deploy `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --src-path $tempZip `
    --type zip `
    --async false `
    --timeout 600 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Deployment completed" -ForegroundColor Green
    Write-Host ""
    
    # Step 3: Restart app
    Write-Host "[3/4] Restarting application..." -ForegroundColor Cyan
    az webapp restart --name $WebAppName --resource-group $ResourceGroup --output none
    Write-Host "  ✓ App restarted" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "[4/4] Waiting for app to initialize (30 seconds)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 30
    Write-Host "  ✓ Ready to test" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "=" * 70 -ForegroundColor Green
    Write-Host " ✅ Deployment Successful!" -ForegroundColor Green -BackgroundColor DarkGreen
    Write-Host "=" * 70 -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Test your application:" -ForegroundColor Cyan
    Write-Host "   https://$WebAppName.azurewebsites.net" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "🔑 Demo Login:" -ForegroundColor Cyan
    Write-Host "   Username: admin" -ForegroundColor Gray
    Write-Host "   Password: admin123" -ForegroundColor Gray
    Write-Host ""
    
} else {
    Write-Host "  ✗ Deployment failed" -ForegroundColor Red
    Write-Host "  Error: $deployOutput" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Try using VS Code Azure App Service extension instead:" -ForegroundColor Yellow
    Write-Host "  • Right-click project → Deploy to Web App → $WebAppName" -ForegroundColor Gray
}

# Cleanup
Remove-Item $tempZip -Force
Write-Host ""
