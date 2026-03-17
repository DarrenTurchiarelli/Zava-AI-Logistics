# Zava - Azure Deployment Guide

## Prerequisites

1. Azure Subscription
2. Azure CLI installed (`az`)
3. PowerShell 7+ (for deployment script)
4. Git installed
5. `.env` file configured with agent IDs and configuration

## Quick Start - Automated Deployment

The recommended way to deploy Zava is using the automated PowerShell deployment script with Bicep:

```powershell
# Login to Azure
az login

# Navigate to project directory
cd c:\Workbench\dt_item_scanner

# Deploy everything (infrastructure + code)
.\deploy_to_azure.ps1

# Or deploy to specific environment
.\deploy_to_azure.ps1 -Environment "production" -Sku "P1v2" -Location "eastus"
```

### What Gets Deployed

The deployment script uses the Bicep template (`infra/main.bicep`) to create:

- ✅ **Cosmos DB** (serverless) with 5 containers
- ✅ **Azure AI Hub & Project** for 9 AI agents
- ✅ **Azure Maps** for route optimization
- ✅ **Speech Services** for voice features
- ✅ **Computer Vision** for OCR
- ✅ **App Service & Plan** (Linux Python 3.11)
- ✅ **Application Insights & Log Analytics**
- ✅ **Storage Account** for AI Hub
- ✅ **RBAC Permissions** (managed identity authentication)
- ✅ **Agent Configuration** (9 agent IDs from `.env`)
- ✅ **Demo Data** (users, manifests, parcels)

### Prerequisites Check

The deployment script **automatically handles**:
- ✅ **Resource Provider Registration**: All required Azure resource providers are registered automatically
  - Microsoft.DocumentDB (Cosmos DB)
  - Microsoft.CognitiveServices (AI, Speech, Vision)
  - Microsoft.Maps, Microsoft.Web, Microsoft.Insights
  - Microsoft.Storage, Microsoft.MachineLearningServices
- ✅ **RBAC Permission Propagation**: Waits for managed identity permissions
- ✅ **Fresh Subscription Support**: Works on brand new Azure subscriptions

No manual portal configuration required!

## Deployment Options

### Full Deployment (First Time)
```powershell
.\deploy_to_azure.ps1
```

### Code-Only Deployment (After Infrastructure Exists)
```powershell
.\deploy_to_azure.ps1 -CodeOnly
```

### Force Complete Redeployment
```powershell
.\deploy_to_azure.ps1 -Force
```

### Custom Configuration
```powershell
.\deploy_to_azure.ps1 `
  -ResourceGroup "my-custom-rg" `
  -Location "australiaeast" `
  -Environment "production" `
  -Sku "P1v2"
```

## Environment File Configuration

Before deploying, ensure your `.env` file contains all required values:

```ini
# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT="https://your-hub.services.ai.azure.com/api/projects/your-project"
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4o-mini"

# Agent IDs (9 agents)
CUSTOMER_SERVICE_AGENT_ID="asst_xxx"
FRAUD_RISK_AGENT_ID="asst_xxx"
IDENTITY_AGENT_ID="asst_xxx"
DISPATCHER_AGENT_ID="asst_xxx"
PARCEL_INTAKE_AGENT_ID="asst_xxx"
SORTING_FACILITY_AGENT_ID="asst_xxx"
DELIVERY_COORDINATION_AGENT_ID="asst_xxx"
OPTIMIZATION_AGENT_ID="asst_xxx"
DRIVER_AGENT_ID="asst_xxx"

# Azure Cosmos DB (created by Bicep deployment)
COSMOS_DB_ENDPOINT="https://your-cosmos.documents.azure.com:443/"
COSMOS_DB_DATABASE_NAME="logisticstracking"

# Azure Maps
AZURE_MAPS_SUBSCRIPTION_KEY="your-key"

# Azure Speech Services
AZURE_SPEECH_RESOURCE_ID="/subscriptions/.../providers/Microsoft.CognitiveServices/accounts/your-speech"
AZURE_SPEECH_REGION="australiaeast"

# Azure Computer Vision
AZURE_VISION_ENDPOINT="https://your-vision.cognitiveservices.azure.com/"
AZURE_VISION_KEY="your-key"

# Depot Addresses (8 Australian states)
DEPOT_NSW="1 Homebush Bay Drive, Rhodes NSW 2138"
DEPOT_VIC="456 Spencer Street, Melbourne VIC 3000"
# ... (remaining depot addresses)
```

## Deployment Script Features

### Automated Infrastructure
- Creates all Azure resources via Bicep template
- Configures RBAC permissions automatically
- Sets up managed identity authentication
- No manual portal configuration needed

### Intelligent Redeployment
- Detects existing deployments
- Preserves Flask session keys
- Updates only changed resources
- Saves deployment configuration to `.azure-deployment.json`

### Post-Deployment Tasks
- Initializes default users (admin, support, drivers)
- Generates demo manifests for all drivers
- Updates agent instructions in Azure AI Foundry
- Tests application endpoint

## Manual Infrastructure Deployment (Advanced)

If you need to deploy infrastructure separately:

```powershell
# Deploy only infrastructure (uses infra/main.bicep)
az deployment group create `
  --name "zava-deployment" `
  --resource-group "RG-Zava-Logistics" `
  --template-file "infra/main.bicep" `
  --parameters location="australiaeast" environment="dev" appServiceSku="B2"
```

## Post-Deployment Verification

### 1. Check Deployment Status
```powershell
# View deployment outputs
az deployment group show `
  --name "zava-deployment-YYYYMMDDHHMMSS" `
  --resource-group "RG-Zava-Logistics" `
  --query "properties.outputs"

# List app services
az webapp list --resource-group "RG-Zava-Logistics" --output table
```

### 2. View Application Logs
```powershell
az webapp log tail `
  --name "zava-dev-web-XXXXXX" `
  --resource-group "RG-Zava-Logistics"
```

### 3. Test Application
Visit the application URL provided in the deployment output:
- Default credentials: `admin` / `admin123`
- Wait 1-2 minutes for RBAC permissions to propagate

## Scaling

### Scale Up (Change SKU)
```powershell
# Update to Premium tier
.\deploy_to_azure.ps1 -Sku "P1v2"

# Or manually via CLI
az appservice plan update `
  --name "zava-dev-plan" `
  --resource-group "RG-Zava-Logistics" `
  --sku "P1v2"
```

### Scale Out (Increase Instances)
```powershell
az appservice plan update `
  --name "zava-dev-plan" `
  --resource-group "RG-Zava-Logistics" `
  --number-of-workers 3
```

### Restart App Service
```powershell
# Find your app service name
az webapp list --resource-group "RG-Zava-Logistics" --query "[].name" -o table

# Restart it
az webapp restart `
  --name "zava-dev-web-XXXXXX" `
  --resource-group "RG-Zava-Logistics"
```

## Monitoring & Diagnostics

### View Live Logs
```powershell
az webapp log tail `
  --name "zava-dev-web-XXXXXX" `
  --resource-group "RG-Zava-Logistics"
```

### View Application Insights
The Bicep deployment includes Application Insights. Access it via:
- Azure Portal → Application Insights → zava-dev-appinsights-XXXXXX
- View: Failures, Performance, Live Metrics, Logs

### Health Check
```powershell
# Test application endpoint
$webAppName = (az webapp list --resource-group "RG-Zava-Logistics" --query "[0].defaultHostName" -o tsv)
Invoke-WebRequest "https://$webAppName/health" -UseBasicParsing
```

## Security Checklist

- ✅ **HTTPS Only**: Enforced by Bicep template
- ✅ **Managed Identity**: Enabled automatically
- ✅ **RBAC Permissions**: Granted during deployment
  - Cosmos DB Data Contributor
  - Cognitive Services OpenAI Contributor  
  - Azure AI Developer
- ✅ **No Connection Strings**: Uses managed identity authentication
- ✅ **Secrets Management**: `.env` file excluded from Git
- ✅ **Cosmos DB**: Local auth disabled (`DisableLocalAuth=true`)
- ✅ **Application Insights**: Enabled with Log Analytics
- ✅ **Network Isolation**: _(Optional)_ Configure VNet integration

### Optional: Enable IP Restrictions
```powershell
az webapp config access-restriction add `
  --name "zava-dev-web-XXXXXX" `
  --resource-group "RG-Zava-Logistics" `
  --rule-name "office" `
  --action Allow `
  --ip-address "203.0.113.0/24" `
  --priority 100
```

## Cost Optimization

### Recommended SKUs by Environment
- **Development**: B2 ($62/month AUD) - Included in deployment
- **Staging**: S1 ($100/month AUD)
- **Production**: P1v2 ($146/month AUD) - Auto-scaling, custom domains

### Cost-Saving Tips
- Use Cosmos DB serverless mode (included in Bicep)
- Enable auto-scaling only on production
- Use Azure Cost Management alerts
- Stop development environments outside business hours

### Set Budget Alert
```powershell
# Create budget alert at $200/month
az consumption budget create `
  --budget-name "zava-monthly-budget" `
  --amount 200 `
  --time-grain Monthly `
  --start-date (Get-Date -Format "yyyy-MM-01") `
  --end-date (Get-Date).AddYears(1).ToString("yyyy-MM-01") `
  --resource-group "RG-Zava-Logistics"
```

## Troubleshooting

### Deployment Fails
```powershell
# Check Bicep deployment errors
az deployment group list `
  --resource-group "RG-Zava-Logistics" `
  --query "[?properties.provisioningState=='Failed']"

# View detailed error
az deployment group show `
  --name "zava-deployment-YYYYMMDDHHMMSS" `
  --resource-group "RG-Zava-Logistics" `
  --query "properties.error"
```

### RBAC Permission Errors
```powershell
# Wait 2-5 minutes for RBAC propagation, then restart app
Start-Sleep -Seconds 300
az webapp restart --name "zava-dev-web-XXXXXX" --resource-group "RG-Zava-Logistics"

# Verify role assignments
$principalId = (az webapp identity show --name "zava-dev-web-XXXXXX" --resource-group "RG-Zava-Logistics" --query "principalId" -o tsv)
az role assignment list --assignee $principalId --all --output table
```

### Login Issues After Deployment
**Symptom**: "Invalid credentials" or "Demo login failed"

**Cause**: RBAC permissions not yet propagated (takes 2-5 minutes)

**Solution**:
- Wait 2-5 minutes after deployment
- App auto-initializes users on first successful connection
- Restart app service to retry: `az webapp restart --name "zava-dev-web-XXXXXX" --resource-group "RG-Zava-Logistics"`

### Agent Errors
```powershell
# Verify all 9 agent IDs are set in .env
Select-String -Path ".env" -Pattern "AGENT_ID"

# Check agent connectivity in logs
az webapp log tail --name "zava-dev-web-XXXXXX" --resource-group "RG-Zava-Logistics" | Select-String "agent"
```

### Database Connection Errors
```powershell
# Test Cosmos DB connection
python parcel_tracking_db.py

# Verify endpoint in app settings
az webapp config appsettings list `
  --name "zava-dev-web-XXXXXX" `
  --resource-group "RG-Zava-Logistics" `
  --query "[?name=='COSMOS_DB_ENDPOINT']"
```

## Useful URLs

After deployment, your application will be available at:
- **App URL**: `https://zava-dev-web-XXXXXX.azurewebsites.net`
- **Admin Portal**: `https://zava-dev-web-XXXXXX.azurewebsites.net/admin`
- **API Health Check**: `https://zava-dev-web-XXXXXX.azurewebsites.net/health`

_(Replace XXXXXX with your unique suffix)_

## CI/CD Integration

### Deploy from GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy with PowerShell
        run: .\deploy_to_azure.ps1 -CodeOnly
        shell: pwsh
```

## Support & Documentation

For additional help:
- 📖 [Main README](../readme.md) - User-focused overview
- 🤖 [AGENTS.md](../AGENTS.md) - Developer documentation
- 🚀 [DEMO_GUIDE.md](DEMO_GUIDE.md) - Feature walkthrough
- 🔐 [USER_AUTH_GUIDE.md](USER_AUTH_GUIDE.md) - Authentication details

**Technical Support:**
- Check Azure Portal → App Service → Diagnose and solve problems
- Review application logs: `az webapp log tail`
- Contact: [GitHub Issues](https://github.com/your-repo/issues)
