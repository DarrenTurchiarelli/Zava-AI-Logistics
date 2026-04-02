# ============================================================================
# Register Agent Tools via Azure Cloud Shell
# Executes register_agent_tools.py in Cloud Shell with proper permissions
# ============================================================================

Write-Host "🚀 Registering Customer Service Agent Tools via Azure Cloud Shell" -ForegroundColor Cyan
Write-Host "=" * 80
Write-Host ""

# Create a script to run in Cloud Shell
$cloudShellScript = @"
#!/bin/bash
set -e

echo "🔧 Setting up environment..."
cd ~
rm -rf Zava-Logistics 2>/dev/null || true
git clone https://github.com/DarrenTurchiarelli/Zava-Logistics.git
cd Zava-Logistics

echo ""
echo "📦 Installing dependencies..."
pip install -q python-dotenv azure-ai-projects azure-identity openai

echo ""
echo "🔧 Creating .env file with production configuration..."
cat > .env << 'EOF'
AZURE_AI_PROJECT_ENDPOINT=https://australiaeast.api.azureml.ms/discovery/subscriptions/728f99b5-49fe-47b9-9bcd-97d981ccdfa9/resourceGroups/RG-Zava-Middleware-dev/providers/Microsoft.MachineLearningServices/workspaces/zava-dev-aiproject-bmwcty
AZURE_OPENAI_ENDPOINT=https://zava-dev-openai-bmwcty.openai.azure.com/
CUSTOMER_SERVICE_AGENT_ID=asst_AiDaSE4LqiHZIHRsiFy5xwJs
COMPANY_NAME=Zava Last Mile Logistics
COMPANY_PHONE=1300 384 669
COMPANY_EMAIL=support@zava.com.au
EOF

echo ""
echo "🤖 Registering agent tools..."
python register_agent_tools.py

echo ""
echo "✅ Done! Agent tools registered successfully."
"@

# Save to temp file
$scriptPath = Join-Path $env:TEMP "register_tools.sh"
$cloudShellScript | Out-File -FilePath $scriptPath -Encoding UTF8

Write-Host "📋 Cloud Shell script created: $scriptPath" -ForegroundColor Green
Write-Host ""
Write-Host "📝 To run this in Azure Cloud Shell:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Open Azure Cloud Shell (Bash): https://shell.azure.com" -ForegroundColor White
Write-Host "2. Paste and run the script above, OR:" -ForegroundColor White
Write-Host "3. Run this one-liner:" -ForegroundColor White
Write-Host ""
Write-Host "cd ~ && rm -rf Zava-Logistics && git clone https://github.com/DarrenTurchiarelli/Zava-Logistics.git && cd Zava-Logistics && pip install -q python-dotenv azure-ai-projects azure-identity openai && python register_agent_tools.py" -ForegroundColor Cyan
Write-Host ""
