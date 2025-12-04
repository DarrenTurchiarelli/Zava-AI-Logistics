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

# Set environment variables
az webapp config appsettings set \
  --name dt-logistics-web \
  --resource-group dt-logistics-rg \
  --settings \
    COSMOS_CONNECTION_STRING="<your_cosmos_connection>" \
    AZURE_AI_PROJECT_CONNECTION_STRING="<your_ai_connection>" \
    FLASK_SECRET_KEY="<generate_secure_key>" \
    FLASK_ENV="production"

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
|----------|-------------|---------|
| `COSMOS_CONNECTION_STRING` | Azure Cosmos DB connection | `AccountEndpoint=https://...` |
| `AZURE_AI_PROJECT_CONNECTION_STRING` | Azure AI Foundry endpoint | `https://...` |
| `FLASK_SECRET_KEY` | Flask session secret | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | Environment mode | `production` |
| `PORT` | Port number (auto-set) | `8000` |

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
- ✅ Managed Identity configured
- ✅ Environment variables set in Azure (not in code)
- ✅ .gitignore includes .env file
- ✅ Authentication configured (for production)
- ✅ IP restrictions enabled (optional)
- ✅ Application Insights monitoring enabled

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
