# Azure Deployment Guide

This guide covers deploying the DT Logistics application to Azure App Service.

## Prerequisites

1. **Azure CLI** installed and logged in
   ```powershell
   az login
   ```

2. **Python 3.11+** installed locally

3. **Cosmos DB Account** with proper configuration:
   - Either **key-based authentication enabled** (recommended for simplicity)
   - OR **Azure AD/RBAC authentication** with proper role assignments

## Quick Deployment

Run the automated deployment script:

```powershell
.\deploy_to_azure.ps1
```

This script will:
1. Create an Azure Resource Group
2. Create an App Service Plan (B2 tier)
3. Create a Web App with Python 3.11 runtime
4. Enable managed identity
5. Configure startup command
6. Set all environment variables from `.env` file
7. **Grant Cosmos DB RBAC permissions** to the managed identity
8. Deploy the application code
9. Configure Always On, logging, and HTTPS
10. Initialize default user accounts

## Environment Variables

The deployment script reads these variables from your `.env` file:

### Required Variables

```bash
# Cosmos DB
COSMOS_DB_ENDPOINT="https://your-account.documents.azure.com:443/"
COSMOS_DB_KEY="your-cosmos-key"
COSMOS_DB_DATABASE_NAME="agent_workflow_db"

# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT="https://your-ai-hub.services.ai.azure.com/api/projects/your-project"
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4o-mini"

# Azure Maps (for route optimization)
AZURE_MAPS_SUBSCRIPTION_KEY="your-maps-key"

# Azure Vision (for OCR/barcode scanning)
AZURE_VISION_ENDPOINT="https://your-vision.cognitiveservices.azure.com/"
AZURE_VISION_KEY="your-vision-key"

# Depot Addresses (for route starting points)
DEPOT_NSW="123 Industrial Drive, Sydney NSW 2000"
DEPOT_VIC="456 Spencer Street, Melbourne VIC 3000"
DEPOT_QLD="789 Creek Street, Brisbane QLD 4000"
DEPOT_SA="321 North Terrace, Adelaide SA 5000"
DEPOT_WA="654 Wellington Street, Perth WA 6000"
DEPOT_TAS="147 Elizabeth Street, Hobart TAS 7000"
DEPOT_ACT="258 Northbourne Avenue, Canberra ACT 2600"
DEPOT_NT="369 Mitchell Street, Darwin NT 0800"
```

## Cosmos DB Authentication

### Option 1: Key-Based Authentication (Recommended)

The application will use the `COSMOS_DB_KEY` from environment variables.

**No additional setup required** - the deployment script handles everything.

### Option 2: Azure AD/RBAC Authentication

If your Cosmos DB has key-based auth disabled (`disableLocalAuth: true`):

1. The deployment script will **automatically grant** the required RBAC role:
   - **Cosmos DB Built-in Data Contributor**

2. If automatic granting fails, grant manually:
   ```powershell
   # Get the managed identity principal ID
   $principalId = az webapp identity show --name YOUR_WEBAPP_NAME --resource-group YOUR_RG --query principalId -o tsv
   
   # Grant Cosmos DB permissions
   az cosmosdb sql role assignment create `
     --account-name YOUR_COSMOS_ACCOUNT `
     --resource-group YOUR_COSMOS_RG `
     --role-definition-name "Cosmos DB Built-in Data Contributor" `
     --principal-id $principalId `
     --scope "/"
   ```

3. **Wait 2-5 minutes** for RBAC permissions to propagate

4. Restart the web app:
   ```powershell
   az webapp restart --name YOUR_WEBAPP_NAME --resource-group YOUR_RG
   ```

## Post-Deployment

### 1. Initialize Users

If user initialization didn't run during deployment:

```powershell
python init_azure_users.py
```

This creates default accounts:
- **admin** / admin123 (Administrator)
- **support** / support123 (Customer Service)
- **driver001, driver002, driver003** / driver123 (Drivers)
- **depot_mgr** / depot123 (Depot Manager)

### 2. Verify Deployment

Visit your application URL: `https://YOUR_WEBAPP_NAME.azurewebsites.net`

Test login with quick demo buttons or manual credentials.

### 3. View Logs

```powershell
# Stream live logs
az webapp log tail --name YOUR_WEBAPP_NAME --resource-group YOUR_RG

# Download logs
az webapp log download --name YOUR_WEBAPP_NAME --resource-group YOUR_RG --log-file app-logs.zip
```

## Troubleshooting

### Login Not Working

**Error:** Authentication fails or returns to login page

**Solution:**
1. Check if Cosmos DB permissions are granted:
   ```powershell
   az cosmosdb sql role assignment list --account-name YOUR_COSMOS_ACCOUNT --resource-group YOUR_COSMOS_RG
   ```

2. Verify managed identity exists:
   ```powershell
   az webapp identity show --name YOUR_WEBAPP_NAME --resource-group YOUR_RG
   ```

3. Check application logs for permission errors:
   ```powershell
   az webapp log tail --name YOUR_WEBAPP_NAME --resource-group YOUR_RG
   ```

4. If you see "Request blocked by Auth" errors, wait 5 minutes for RBAC propagation, then restart:
   ```powershell
   az webapp restart --name YOUR_WEBAPP_NAME --resource-group YOUR_RG
   ```

### Environment Variables Not Set

**Error:** Application can't find configuration

**Solution:**
1. Verify environment variables in Azure Portal or:
   ```powershell
   az webapp config appsettings list --name YOUR_WEBAPP_NAME --resource-group YOUR_RG
   ```

2. Re-run deployment to update settings:
   ```powershell
   .\deploy_to_azure.ps1
   ```

### Cosmos DB Connection Fails

**Error:** "Failed to connect to Cosmos DB"

**Solution:**
1. Check if your IP is allowed in Cosmos DB firewall
2. Verify Cosmos DB endpoint and key are correct
3. For Azure AD auth, ensure RBAC role is assigned

## Updating the Application

To deploy code changes:

```powershell
.\deploy_to_azure.ps1
```

The script will:
- Detect existing resources and reuse them
- Update environment variables from `.env`
- Deploy new application code
- Restart the web app automatically

## Custom Deployment Parameters

```powershell
.\deploy_to_azure.ps1 `
  -ResourceGroup "my-rg" `
  -Location "australiaeast" `
  -AppServicePlan "my-plan" `
  -WebAppName "my-app-unique-name" `
  -Sku "P1v2"
```

### SKU Options
- **F1** - Free tier (limited, no Always On)
- **B1, B2, B3** - Basic tier
- **S1, S2, S3** - Standard tier
- **P1v2, P2v2, P3v2** - Premium tier (recommended for production)

## Security Recommendations

1. **Change Default Passwords** - Update user passwords after first deployment
2. **Use Managed Identity** - Preferred over key-based auth for Cosmos DB
3. **Enable HTTPS Only** - Automatically configured by deployment script
4. **Restrict Cosmos DB Access** - Add App Service IP to Cosmos DB firewall
5. **Use Key Vault** - For production, store secrets in Azure Key Vault

## Cost Optimization

- **B1 SKU** - ~$13/month (development)
- **B2 SKU** - ~$54/month (testing) ← Current default
- **P1v2 SKU** - ~$96/month (production)

- **Cosmos DB Serverless** - Pay per request (recommended for development)
- **Azure Maps** - Free tier: 250,000 transactions/month

## Support

For issues or questions:
1. Check application logs
2. Review this deployment guide
3. Verify all environment variables are set
4. Ensure Cosmos DB permissions are granted

## Architecture

```
┌─────────────────────────────────────────────┐
│         Azure App Service (Web App)         │
│  - Python 3.11                              │
│  - Flask application                        │
│  - Managed Identity enabled                 │
└─────────────────┬───────────────────────────┘
                  │
                  ├─────────► Azure Cosmos DB
                  │            (RBAC auth)
                  │
                  ├─────────► Azure AI Foundry
                  │            (AI agents)
                  │
                  ├─────────► Azure Maps
                  │            (route optimization)
                  │
                  └─────────► Azure Vision
                               (OCR/barcode scanning)
```
