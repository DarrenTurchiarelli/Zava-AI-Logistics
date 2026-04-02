#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick script to register tools with Customer Service Agent
.DESCRIPTION
    Temporarily enables API key, registers tools, then disables it
#>

param(
    [string]$ResourceGroup = "RG-Zava-Middleware-dev",
    [string]$OpenAIName = "zava-dev-openai-bmwcty"
)

Write-Host "=== Quick Tool Registration ===" -ForegroundColor Cyan
Write-Host ""

# Get current auth status
Write-Host "📋 Checking current Azure OpenAI authentication..." -ForegroundColor Yellow
$currentConfig = az cognitiveservices account show `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --query "{disableLocalAuth: properties.disableLocalAuth}" `
    -o json | ConvertFrom-Json

if ($currentConfig.disableLocalAuth -eq $false) {
    Write-Host "   ✓ API key authentication already enabled" -ForegroundColor Green
} else {
    Write-Host "   Enabling API key authentication temporarily..." -ForegroundColor Yellow
    az cognitiveservices account update `
        --name $OpenAIName `
        --resource-group $ResourceGroup `
        --custom-domain $OpenAIName `
        --api-properties @{disableLocalAuth=$false} `
        -o none
    
    Write-Host "   Waiting 15 seconds for configuration to propagate..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
}

# Get API key
Write-Host ""
Write-Host "🔑 Retrieving API key..." -ForegroundColor Yellow
$apiKey = az cognitiveservices account keys list `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --query "key1" `
    -o tsv

if (-not $apiKey) {
    Write-Host "❌ Failed to retrieve API key" -ForegroundColor Red
    exit 1
}

Write-Host "   ✓ API key retrieved" -ForegroundColor Green

# Set environment variable temporarily
$env:AZURE_OPENAI_API_KEY = $apiKey

# Run registration script
Write-Host ""
Write-Host "🔧 Running tool registration script..." -ForegroundColor Yellow
Write-Host ""

python Scripts\register_agent_tools_openai.py

$registrationExitCode = $LASTEXITCODE

# Disable API key authentication
Write-Host ""
Write-Host "🔒 Disabling API key authentication (back to managed identity only)..." -ForegroundColor Yellow
az cognitiveservices account update `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --custom-domain $OpenAIName `
    --api-properties @{disableLocalAuth=$true} `
    -o none

Write-Host "   ✓ API key authentication disabled" -ForegroundColor Green

# Check result
Write-Host ""
if ($registrationExitCode -eq 0) {
    Write-Host "✅ Tool registration completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Wait 2-3 minutes for changes to propagate"
    Write-Host "  2. Test at: https://zava-dev-web-bmwcty.azurewebsites.net/chat"
    Write-Host "  3. Query: 'Can I get photo proof for parcel BC2CEE0A7C90DE?'"
} else {
    Write-Host "❌ Tool registration failed (exit code: $registrationExitCode)" -ForegroundColor Red
    Write-Host "   Check the output above for errors"
}

Write-Host ""
