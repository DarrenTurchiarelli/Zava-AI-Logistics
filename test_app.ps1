# Quick test script to check if app is working
Write-Host "`n🧪 Testing Zava App`n" -ForegroundColor Cyan

$url = "https://zava-dev-web-aixqdm.azurewebsites.net"

try {
    Write-Host "Testing: $url" -ForegroundColor Yellow
    $response = Invoke-WebRequest -Uri $url -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
    
    Write-Host "`n✅ SUCCESS! App is working!" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode) $($response.StatusDescription)`n" -ForegroundColor Gray
    Write-Host "🎉 Your app is ready to use!" -ForegroundColor Green
    Write-Host "   URL: $url" -ForegroundColor Cyan
    Write-Host "   Login: admin / admin123`n" -ForegroundColor White
    
} catch {
    $errorMsg = $_.Exception.Message
    
    if ($errorMsg -match "Application Error") {
        Write-Host "`n❌ Application Error - App needs redeployment" -ForegroundColor Red
        Write-Host "   The application code may not be deployed correctly`n" -ForegroundColor Gray
    } elseif ($errorMsg -match "timeout|timed out") {
        Write-Host "`n⏱  Timeout - App is still starting" -ForegroundColor Yellow
        Write-Host "   Wait 30 more seconds and try again`n" -ForegroundColor Gray
    } elseif ($errorMsg -match "503") {
        Write-Host "`n⚠️  Service Unavailable (503) - App is starting" -ForegroundColor Yellow
        Write-Host "   This is normal after deployment - wait 30-60 seconds`n" -ForegroundColor Gray
    } else {
        Write-Host "`n⚠️  Error: $errorMsg`n" -ForegroundColor Yellow
    }
    
    Write-Host "Check logs:" -ForegroundColor Cyan
    Write-Host "   az webapp log tail --name zava-dev-web-aixqdm --resource-group RG-Zava-Frontend-dev`n" -ForegroundColor White
}
