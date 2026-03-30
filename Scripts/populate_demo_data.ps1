# Populate Demo Data
# Run this after deployment to generate all demo data

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Populating Demo Data" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Configure Azure AD authentication (clear any stale connection strings)
Write-Host "Configuring Azure AD authentication..." -ForegroundColor Cyan
Remove-Item Env:\COSMOS_CONNECTION_STRING -ErrorAction SilentlyContinue
$env:COSMOS_DB_ENDPOINT = "https://zava-dev-cosmos-77cd5n.documents.azure.com:443/"
$env:COSMOS_DB_DATABASE_NAME = "logisticstracking"
$env:USE_MANAGED_IDENTITY = "false"
$env:PYTHONPATH = "$PWD"
Write-Host "✓ Using Azure AD (AzureCliCredential) for authentication" -ForegroundColor Green
Write-Host ""

# Step 1: Generate fresh test parcels
Write-Host "[1/4] Generating fresh test parcels with DC assignments..." -ForegroundColor Yellow
python utils\generators\generate_fresh_test_data.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Fresh test data generated" -ForegroundColor Green
} else {
    Write-Host "⚠ Fresh test data generation had issues" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Generate dispatcher demo data
Write-Host "[2/4] Generating parcels ready for dispatcher assignment..." -ForegroundColor Yellow
python utils\generators\generate_dispatcher_demo_data.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dispatcher demo data generated" -ForegroundColor Green
} else {
    Write-Host "⚠ Dispatcher demo data generation had issues" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Generate driver manifests
Write-Host "[3/4] Generating driver manifests with delivery parcels..." -ForegroundColor Yellow
python utils\generators\generate_demo_manifests.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Demo manifests generated for all drivers" -ForegroundColor Green
} else {
    Write-Host "⚠ Demo manifest generation had issues" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Create approval demo requests
Write-Host "[4/4] Creating approval demo requests..." -ForegroundColor Yellow
python utils\generators\create_approval_requests.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Approval demo requests created" -ForegroundColor Green
} else {
    Write-Host "⚠ Approval request creation had issues (non-critical)" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "=" * 80 -ForegroundColor Green
Write-Host "✅ Demo Data Population Complete!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  • Visit: https://zava-dev-web-77cd5n.azurewebsites.net/parcels/all" -ForegroundColor Gray
Write-Host "  • Login as: driver001 (password: driver123)" -ForegroundColor Gray
Write-Host "  • Check manifests: https://zava-dev-web-77cd5n.azurewebsites.net/manifest" -ForegroundColor Gray
Write-Host "  • View approvals: https://zava-dev-web-77cd5n.azurewebsites.net/approvals" -ForegroundColor Gray
Write-Host ""
