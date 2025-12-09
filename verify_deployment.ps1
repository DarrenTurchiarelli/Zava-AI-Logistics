# Verify DT Logistics Deployment
param(
    [string]$WebAppUrl = "https://dt-logistics-web-5545.azurewebsites.net"
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " DT Logistics - Deployment Verification" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Setup Users
Write-Host "[1/4] Setting up default users..." -ForegroundColor Yellow
try {
    $setupUrl = "$WebAppUrl/admin/setup-users-now"
    $response = Invoke-WebRequest -Uri $setupUrl -UseBasicParsing -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Users setup successful" -ForegroundColor Green
        Write-Host "  Response: $($response.Content.Substring(0, [Math]::Min(200, $response.Content.Length)))" -ForegroundColor Gray
    } else {
        Write-Host "⚠ Unexpected status code: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Setup failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 2: Health Check
Write-Host "[2/4] Checking application health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $WebAppUrl -UseBasicParsing -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Application is running" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Login Page
Write-Host "[3/4] Checking login page..." -ForegroundColor Yellow
try {
    $loginUrl = "$WebAppUrl/login"
    $response = Invoke-WebRequest -Uri $loginUrl -UseBasicParsing -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Login page accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Login page check failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 4: Test Login
Write-Host "[4/4] Testing login with admin credentials..." -ForegroundColor Yellow
try {
    $loginUrl = "$WebAppUrl/login"
    $body = @{
        username = "admin"
        password = "admin123"
    }
    
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $response = Invoke-WebRequest -Uri $loginUrl -Method Post -Body $body -WebSession $session -UseBasicParsing -TimeoutSec 30 -MaximumRedirection 0 -ErrorAction SilentlyContinue
    
    if ($response.StatusCode -eq 302 -or $response.StatusCode -eq 200) {
        Write-Host "✓ Login test successful" -ForegroundColor Green
    } else {
        Write-Host "⚠ Login returned status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 302) {
        Write-Host "✓ Login successful (redirected)" -ForegroundColor Green
    } else {
        Write-Host "⚠ Login test info: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}
Write-Host ""

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Default Login Credentials" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Username: admin       Password: admin123" -ForegroundColor White
Write-Host "  Username: support     Password: support123" -ForegroundColor White
Write-Host "  Username: driver001   Password: driver123" -ForegroundColor White
Write-Host "  Username: depot_mgr   Password: depot123" -ForegroundColor White
Write-Host ""
Write-Host "Application URL: $WebAppUrl" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
