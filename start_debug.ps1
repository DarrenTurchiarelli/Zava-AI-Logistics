# Development Mode - Full Debug Output
# All debug statements enabled for troubleshooting

$env:FLASK_ENV='development'
$env:DEBUG_MODE='true'

Write-Host "🔧 Starting Flask in DEVELOPMENT mode (debug enabled)" -ForegroundColor Cyan
Write-Host "   - Flask debugger: ON" -ForegroundColor Yellow
Write-Host "   - Debug print statements: ON" -ForegroundColor Yellow
Write-Host "   - Console logging: Full" -ForegroundColor Yellow
Write-Host "   - Auto-reload: ENABLED" -ForegroundColor Yellow
Write-Host ""

python app.py
