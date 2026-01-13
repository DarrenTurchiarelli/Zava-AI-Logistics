# Zava - Azure App Service Deployment Guide

## Prerequisites

1. Azure Subscription
2. Azure CLI installed (`az`)
3. Azure Developer CLI installed (`azd`)
4. Git installed

## Deployment Steps

### Option 1: Deploy with Azure Developer CLI (Recommended)

```bash
# Login to Azure
azd auth login

# Initialize and provision resources
azd up

# Follow prompts to:
# - Select subscription
# - Choose region (e.g., australiaeast)
# - Name your resources
```

### Option 2: Deploy with Azure CLI

```bash
# Login to Azure
az login

# Create Resource Group
az group create --name dt-logistics-rg --location australiaeast

# Create App Service Plan
az appservice plan create \
  --name dt-logistics-plan \
  --resource-group dt-logistics-rg \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --plan dt-logistics-plan \
  --runtime "PYTHON:3.11"

# Configure startup command
az webapp config set \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers=4 app:app"

# Enable managed identity (recommended for production)
az webapp identity assign \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg

# Set environment variables
az webapp config appsettings set \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --settings \
    COSMOS_DB_ENDPOINT="<your_cosmos_endpoint>" \
    COSMOS_DB_DATABASE_NAME="<your_database_name>" \
    AZURE_AI_PROJECT_CONNECTION_STRING="<your_ai_connection>" \
    AZURE_SPEECH_KEY="<your_speech_key>" \
    AZURE_SPEECH_REGION="<your_region>" \
    FLASK_SECRET_KEY="<generate_secure_key>" \
    FLASK_ENV="production" \
    USE_MANAGED_IDENTITY="true"

# Deploy code
az webapp up \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --runtime "PYTHON:3.11"
```

### Option 3: Deploy from GitHub

1. Push code to GitHub repository
2. In Azure Portal, go to your App Service
3. Select "Deployment Center"
4. Choose GitHub as source
5. Authenticate and select repository
6. Azure will auto-deploy on every push

## Environment Variables (Required)

Set these in Azure Portal → App Service → Configuration → Application Settings:

| Variable | Description | Example |
|----------|-------------|---------|------|
| `COSMOS_DB_ENDPOINT` | Azure Cosmos DB endpoint URL | `https://your-cosmos.documents.azure.com:443/` |
| `COSMOS_DB_DATABASE_NAME` | Cosmos DB database name | `logisticstracking` |
| `AZURE_AI_PROJECT_CONNECTION_STRING` | Azure AI Foundry endpoint | `https://your-hub.services.ai.azure.com/api/projects/your-project` |
| `AZURE_SPEECH_KEY` | Azure Speech Services key | `your-speech-key` |
| `AZURE_SPEECH_REGION` | Azure Speech Services region | `australiaeast` |
| `FLASK_SECRET_KEY` | Flask session secret | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | Environment mode | `production` |
| `USE_MANAGED_IDENTITY` | Enable managed identity auth | `true` |
| `PORT` | Port number (auto-set) | `8000` |

**Note**: Do NOT set `COSMOS_CONNECTION_STRING` or `COSMOS_DB_KEY` when using managed identity authentication.

## RBAC Permissions (Required for Managed Identity)

After enabling managed identity, grant the following Azure RBAC roles to the App Service's managed identity:

### 1. Cosmos DB Access

```bash
# Get the managed identity principal ID
PRINCIPAL_ID=$(az webapp identity show \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --query principalId -o tsv)

# Assign Cosmos DB Built-in Data Contributor role
az cosmosdb sql role assignment create \
  --account-name your-cosmos-account \
  --resource-group dt-logistics-rg \
  --role-definition-id 00000000-0000-0000-0000-000000000002 \
  --principal-id $PRINCIPAL_ID \
  --scope "/"
```

### 2. Azure AI Foundry Access

```bash
# Get subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Assign Cognitive Services OpenAI Contributor role
az role assignment create \
  --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services OpenAI Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/dt-logistics-rg"

# Assign Azure AI Developer role (for agents/write operations)
az role assignment create \
  --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Azure AI Developer" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/dt-logistics-rg"

# Assign Cognitive Services User role (for agents/read operations)
az role assignment create \
  --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services User" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/dt-logistics-rg"

# CRITICAL: Assign roles to the specific AI Hub resource (required for agents/read)
# Find your AI Hub resource ID
AI_HUB_RESOURCE_ID=$(az resource list \
  --query "[?contains(name, 'dtaihub') && type=='Microsoft.CognitiveServices/accounts'].id | [0]" \
  -o tsv)

echo "AI Hub Resource: $AI_HUB_RESOURCE_ID"

# Assign Cognitive Services Contributor to AI Hub (includes all agent operations)
az role assignment create \
  --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services Contributor" \
  --scope "$AI_HUB_RESOURCE_ID"

# Assign Azure AI Developer to AI Hub
az role assignment create \
  --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Azure AI Developer" \
  --scope "$AI_HUB_RESOURCE_ID"

# Assign Cognitive Services OpenAI Contributor to AI Hub
az role assignment create \
  --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services OpenAI Contributor" \
  --scope "$AI_HUB_RESOURCE_ID"
```

### 3. Verify Role Assignments

```bash
# List all role assignments for the managed identity
az role assignment list \
  --assignee $PRINCIPAL_ID \
  --all \
  --query "[].{Role:roleDefinitionName, Scope:scope}" \
  --output table
```

### Required Roles Summary

| Service | Role | Scope | Purpose |
|---------|------|-------|---------|
| **Cosmos DB** | `Cosmos DB Built-in Data Contributor` | Cosmos DB Account | Full data plane access (CRUD operations) |
| **AI Foundry (RG)** | `Cognitive Services OpenAI Contributor` | Resource Group | OpenAI model operations |
| **AI Foundry (RG)** | `Azure AI Developer` | Resource Group | General agent permissions |
| **AI Foundry (RG)** | `Cognitive Services User` | Resource Group | Agent read operations |
| **AI Hub (Resource)** | `Cognitive Services Contributor` | AI Hub Resource | **CRITICAL**: Includes agents/read data action |
| **AI Hub (Resource)** | `Azure AI Developer` | AI Hub Resource | Agent write/execute on specific resource |
| **AI Hub (Resource)** | `Cognitive Services OpenAI Contributor` | AI Hub Resource | OpenAI operations on specific resource |
| **Azure Speech** | Configured via API key | N/A | Speech synthesis and recognition |

**⚠️ CRITICAL**: The `agents/read` permission requires roles assigned directly to the AI Hub **resource**, not just the resource group. Without this, chatbot and fraud detection will fail with permission errors.

**Important**: Role assignments can take up to 5 minutes to propagate. Restart the App Service after granting permissions:

```bash
az webapp restart --name dt-logistics-web --resource-group dt-logistics-rg
```

## Post-Deployment Configuration

### 1. Generate Demo Data (First-Time Setup)

After your first deployment, populate the database with sample parcels and driver manifests:

**Automatic (via deploy_to_azure.ps1):**
The deployment script automatically runs post-deployment tasks that create:

- ✅ Default user accounts (admin, support, drivers, depot_mgr)
- ✅ 57 driver manifests (driver-001 through driver-057)
- ✅ Sample parcels distributed across Australian states
- ✅ Ready-to-use demo environment

**Manual (if needed):**

```bash
# If automatic setup failed or you need to regenerate data

# Generate demo manifests for all 57 drivers
cd utils/generators
python generate_demo_manifests.py

# OR generate large scalability test for driver-004 (120 parcels)
python generate_demo_manifests.py --large-default

# OR generate custom large manifest
python generate_demo_manifests.py --large 200
```

**What this creates:**

- Sample parcels across NSW, VIC, QLD, SA, WA, ACT
- Driver manifests with 30-50 parcels each
- Realistic Sydney addresses and delivery details
- Immediate testing capability for all features

### 2. Enable Always On

```bash
az webapp config set \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --always-on true
```

### 3. Configure Logging

```bash
az webapp log config \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --application-logging filesystem \
  --detailed-error-messages true \
  --web-server-logging filesystem
```

### 4. View Logs

```bash
az webapp log tail \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg
```

## Custom Domain & SSL

```bash
# Map custom domain
az webapp config hostname add \
  --webapp-name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --hostname yourdomain.com

# Enable HTTPS
az webapp update \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --https-only true
```

## Scaling

```bash
# Scale up (change App Service Plan)
az appservice plan update \
  --name dt-logistics-plan \
  --resource-group dt-logistics-rg \
  --sku P1V2

# Scale out (increase instances)
az appservice plan update \
  --name dt-logistics-plan \
  --resource-group dt-logistics-rg \
  --number-of-workers 3
```

## Monitoring

```bash
# Enable Application Insights
az monitor app-insights component create \
  --app dt-logistics-insights \
  --location australiaeast \
  --resource-group dt-logistics-rg

# Link to App Service
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app dt-logistics-insights \
  --resource-group dt-logistics-rg \
  --query instrumentationKey -o tsv)

az webapp config appsettings set \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

## Troubleshooting

### Check Application Logs

```bash
az webapp log tail --name dt-logistics-web --resource-group dt-logistics-rg
```

### SSH into Container

```bash
az webapp ssh --name dt-logistics-web --resource-group dt-logistics-rg
```

### Restart App

```bash
az webapp restart --name dt-logistics-web --resource-group dt-logistics-rg
```

## Security Checklist

- ✅ HTTPS enabled
- ✅ Managed Identity enabled and assigned
- ✅ RBAC roles granted (Cosmos DB, Azure AI, Speech Services)
- ✅ Environment variables set in Azure (not in code)
- ✅ Connection strings removed (using managed identity)
- ✅ .gitignore includes .env file
- ✅ Authentication configured (for production)
- ✅ IP restrictions enabled (optional)
- ✅ Application Insights monitoring enabled
- ✅ Cosmos DB key-based auth disabled (`DisableLocalAuth=true`)

## Cost Optimization

- Use B1 Basic tier for development ($13/month)
- Use P1V2 Premium for production ($146/month)
- Enable auto-scaling based on CPU/Memory
- Use Azure Cost Management alerts

## URLs

- App URL: `https://dt-logistics-web.azurewebsites.net`
- SCM URL: `https://dt-logistics-web.scm.azurewebsites.net`
- Health Check: `https://dt-logistics-web.azurewebsites.net/health`

## Support

For issues or questions:

- Check Azure Portal → App Service → Diagnose and solve problems
- Review application logs
- Contact Azure Support
