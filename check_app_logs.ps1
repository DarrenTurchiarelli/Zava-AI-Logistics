# Quick script to check Azure App Service logs
Write-Host "`n🔍 Checking Application Logs (last 50 lines)`n" -ForegroundColor Cyan

az webapp log tail `
    --name zava-dev-web-aixqdm `
    --resource-group RG-Zava-Frontend-dev `
    2>&1 | Select-Object -Last 50

Write-Host "`n✅ Log check complete`n" -ForegroundColor Green
