# One-Click Azure Deployment

Deploy the complete Zava infrastructure to Azure using Bicep (Infrastructure as Code).

## Prerequisites

- Azure CLI installed (`az --version`)
- Active Azure subscription
- Contributor access to subscription or resource group

# One-Click Azure Deployment

Deploy the complete Zava infrastructure to Azure using Bicep (Infrastructure as Code).

## Prerequisites

- Azure CLI installed (`az --version`)
- Active Azure subscription
- Contributor access to subscription or resource group
- Python 3.11+ (for demo data generation)

## ⚡ Quick Deploy

**Option 1: Using Bicep (Infrastructure Only)**

```bash
# Deploy Azure infrastructure
az group create --name zava-rg --location australiaeast
az deployment group create \
  --resource-group zava-rg \
  --template-file infra/main.bicep \
  --parameters environment=dev

# Then follow manual setup steps below
```

**Option 2: Using PowerShell Script (Recommended)**

```powershell
# Clone repository
git clone https://github.com/DarrenTurchiarelli/dt_item_scanner.git
cd dt_item_scanner

# Configure .env file with Azure credentials (see readme.md)
cp .env.example .env
# Edit .env with your Azure AI and Cosmos DB details

# Run deployment script (handles everything)
.\deploy_to_azure.ps1
```

**What the PowerShell script does:**

- ✅ Creates App Service Plan & Web App
- ✅ Enables Managed Identity
- ✅ Configures RBAC permissions (Cosmos DB, Azure AI)
- ✅ Deploys application code
- ✅ Initializes default users (admin/admin123)
- ✅ Generates demo data (57 drivers, 1000+ parcels)
- ✅ Updates Azure AI agent instructions
- ✅ Auto-configures agent IDs (if .agent-ids.json exists)

## Manual Steps Required

## What Gets Deployed

✅ **Fully Automated:**

1. Azure Cosmos DB (Serverless) - Database with all 5 containers
2. Azure Maps - Route optimization
3. Azure Speech Services - Voice features
4. Azure Computer Vision - OCR capabilities
5. Azure AI Foundry Hub & Project - AI infrastructure
6. App Service Plan & Web App - Hosting
7. Application Insights - Monitoring
8. Log Analytics - Logging
9. Storage Account - AI Hub requirements
10. **RBAC permissions** - Managed identity access

## Manual Steps Required

**These cannot be automated (Azure limitations):**

1. **Create Azure Resources** (if not using Bicep)
   - Azure Cosmos DB account (SQL API, Serverless)
   - Azure AI Foundry Hub & Project
   - Deploy GPT-4o model in AI Foundry

2. **Create 8 AI Agents** (~15 minutes)

   Visit <https://ai.azure.com> → Your Project → Create Agent

   Use these agent configurations:

   | Agent | Instructions |
   |-------|-------------|
   | Customer Service | Handle tracking inquiries, use tools: track_parcel, search_parcels |
   | Fraud Detection | Analyze messages for fraud, provide risk scores 0-100% |
   | Identity Verification | Verify identity for high-risk cases (fraud ≥85%) |
   | Dispatcher | Optimize parcel-to-driver assignments, max 20 parcels/driver |
   | Parcel Intake | Validate new parcels, recommend service types |
   | Sorting Facility | Monitor capacity, optimize routing decisions |
   | Delivery Coordination | Sequence deliveries, manage customer notifications |
   | Optimization | Network-wide analysis, cost reduction recommendations |

   Full instructions in: [AGENTS.md](../AGENTS.md)

3. **Save Agent IDs**

   Create `.agent-ids.json` in repository root:

   ```json
   {
     "CUSTOMER_SERVICE_AGENT_ID": "asst_xxxxxxxxxxxxx",
     "FRAUD_RISK_AGENT_ID": "asst_xxxxxxxxxxxxx",
     "IDENTITY_AGENT_ID": "asst_xxxxxxxxxxxxx",
     "DISPATCHER_AGENT_ID": "asst_xxxxxxxxxxxxx",
     "PARCEL_INTAKE_AGENT_ID": "asst_xxxxxxxxxxxxx",
     "SORTING_FACILITY_AGENT_ID": "asst_xxxxxxxxxxxxx",
     "DELIVERY_COORDINATION_AGENT_ID": "asst_xxxxxxxxxxxxx",
     "OPTIMIZATION_AGENT_ID": "asst_xxxxxxxxxxxxx"
   }
   ```

4. **Re-run Deployment**

   ```powershell
   .\deploy_to_azure.ps1
   ```

   The script will detect `.agent-ids.json` and automatically configure App Service.

## Why Can't Agents Be Auto-Created?

Azure AI Foundry agent creation API is **preview-only** (not production-ready):

- ❌ Limited API functionality
- ❌ No stable CLI commands
- ❌ Tool registration requires portal
- ✅ Manual creation ensures proper configuration

## Deployment Parameters

| Parameter | Default | Options | Description |
|-----------|---------|---------|-------------|
| `environment` | `dev` | `dev`, `staging`, `production` | Environment name |
| `location` | `australiaeast` | Any Azure region | Primary location |
| `appServiceSku` | `B2` | `B1`, `B2`, `B3`, `P1v2`, `P2v2` | App Service tier |

## Custom Deployment

```bash
az deployment group create \
  --resource-group zava-rg \
  --template-file infra/main.bicep \
  --parameters \
    environment=production \
    location=australiaeast \
    appServiceSku=P1v2
```

## Cost Estimate

**Development (B2):** ~$80-120 AUD/month

- App Service B2: ~$50/month
- Cosmos DB Serverless: ~$5-10/month (usage-based)
- Azure Maps G2: ~$10/month
- Speech Services: ~$5/month
- Computer Vision: ~$5/month
- AI Foundry: ~$10-20/month (GPT-4o usage)

**Production (P1v2):** ~$180-250 AUD/month

- App Service P1v2: ~$120/month
- Cosmos DB: ~$10-30/month
- Other services: ~$40/month
- AI Foundry: ~$30-60/month

## Troubleshooting

### Agent Creation Not Automated?

Azure AI Foundry agent creation via API is in **preview** and not production-ready. Manual creation via portal ensures:

- ✅ Proper tool configuration
- ✅ Instruction validation
- ✅ Debugging visibility

### RBAC Permissions Delay

Wait 2-5 minutes after deployment for RBAC roles to propagate before testing.

### Deployment Failed

```bash
# Check deployment logs
az deployment group show \
  --resource-group zava-rg \
  --name <deployment-name> \
  --query properties.error

# Retry deployment
az deployment group create \
  --resource-group zava-rg \
  --template-file infra/main.bicep \
  --parameters environment=dev
```

## Alternative: PowerShell Script

If you prefer the existing PowerShell deployment (assumes you already created AI/Cosmos resources):

```powershell
.\deploy_to_azure.ps1
```

This requires manual setup of all Azure resources first, then configures App Service only.

## Cleanup

```bash
# Delete entire resource group and all resources
az group delete --name zava-rg --yes --no-wait
```

## Next: Complete Setup Guide

After infrastructure deployment, see:

- [readme.md](../readme.md) - Application setup
- [AGENTS.md](../AGENTS.md) - Agent configuration
- [Guides/AZURE_DEPLOYMENT.md](../Guides/AZURE_DEPLOYMENT.md) - Detailed deployment guide
