# Production Mode - Optimized for Performance
# No debug output, faster response times

# Clear any existing environment variables
Remove-Item Env:\FLASK_ENV -ErrorAction SilentlyContinue
Remove-Item Env:\DEBUG_MODE -ErrorAction SilentlyContinue

Write-Host "🚀 Starting Flask in PRODUCTION mode (debug disabled)" -ForegroundColor Green
Write-Host "   - Flask debugger: OFF" -ForegroundColor Yellow
Write-Host "   - Debug print statements: OFF" -ForegroundColor Yellow
Write-Host "   - Console logging: Minimal" -ForegroundColor Yellow
Write-Host "   - Performance: OPTIMIZED ⚡" -ForegroundColor Green
Write-Host ""

python app.py
