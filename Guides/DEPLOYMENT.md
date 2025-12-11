# DT Logistics - Azure App Service Deployment Guide

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

| Service | Role | Purpose |
|---------|------|---------|------|
| **Cosmos DB** | `Cosmos DB Built-in Data Contributor` | Full data plane access (CRUD operations) |
| **Azure AI Foundry** | `Cognitive Services OpenAI Contributor` | OpenAI model and agent operations |
| **Azure AI Foundry** | `Azure AI Developer` | Agents create/write/execute permissions |
| **Azure Speech** | Configured via API key | Speech synthesis and recognition |

**Important**: Role assignments can take up to 5 minutes to propagate. Restart the App Service after granting permissions:
```bash
az webapp restart --name dt-logistics-web --resource-group dt-logistics-rg
```

## Post-Deployment Configuration

### Enable Always On
```bash
az webapp config set \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --always-on true
```

### Configure Logging
```bash
az webapp log config \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --application-logging filesystem \
  --detailed-error-messages true \
  --web-server-logging filesystem
```

### View Logs
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
