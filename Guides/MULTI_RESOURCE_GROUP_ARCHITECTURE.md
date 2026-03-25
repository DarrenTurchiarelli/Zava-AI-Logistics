# Multi-Resource Group Architecture

This document describes the new multi-resource group architecture for the Zava logistics platform.

## Architecture Overview

The infrastructure is organized into **4 logical resource groups** for better security, management, and scalability:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Azure Subscription                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────┐  ┌───────────────────┐                 │
│  │  Frontend RG      │  │  Middleware RG    │                 │
│  │  -------------    │  │  --------------   │                 │
│  │  • App Service    │  │  • Azure OpenAI   │                 │
│  │  • App Plan       │  │  • AI Hub         │                 │
│  │  • App Insights   │  │  • AI Project     │                 │
│  └─────────┬─────────┘  │  • Storage        │                 │
│            │            └────────┬──────────┘                 │
│            │                     │                            │
│            └──────────┬──────────┘                            │
│                       │                                       │
│  ┌───────────────────┴┐  ┌───────────────────┐               │
│  │  Backend RG        │  │  Shared RG        │               │
│  │  -----------       │  │  ----------       │               │
│  │  • Cosmos DB       │  │  • Azure Maps     │               │
│  │  • All Containers  │  │  • Speech Service │               │
│  └────────────────────┘  │  • Vision Service │               │
│                          │  • Log Analytics  │               │
│                          └───────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## Resource Groups

### 1. Frontend Resource Group
**Name:** `RG-Zava-Frontend-{environment}`  
**Purpose:** Web application tier  
**Resources:**
- App Service Plan (Linux, Python 3.11)
- App Service (Web App)
- Application Insights

**Why separate?**
- Independent scaling of web tier
- Isolated permissions for web app developers
- Separate cost tracking for frontend resources

### 2. Middleware Resource Group
**Name:** `RG-Zava-Middleware-{environment}`  
**Purpose:** AI and intelligence layer  
**Resources:**
- Azure OpenAI Service (GPT-4o)
- Azure AI Hub
- Azure AI Project
- Storage Account (for AI Hub)

**Why separate?**
- Centralized AI resource management
- Specialized permissions for AI/ML team
- GPT quotas and monitoring in one place
- Reusable across multiple frontends

### 3. Backend Resource Group
**Name:** `RG-Zava-Backend-{environment}`  
**Purpose:** Data persistence layer  
**Resources:**
- Cosmos DB Account
- All Cosmos DB Databases & Containers:
  - parcels
  - parcel_events
  - driver_manifests
  - users
  - address_notes

**Why separate?**
- Database-specific RBAC and security policies
- Independent backup and disaster recovery
- Simplified data residency compliance
- Dedicated DBA access without web app access

### 4. Shared Services Resource Group
**Name:** `RG-Zava-Shared-{environment}`  
**Purpose:** Reusable services and monitoring  
**Resources:**
- Azure Maps (Gen2)
- Speech Services
- Computer Vision
- Log Analytics Workspace

**Why separate?**
- Services reusable across multiple applications
- Centralized monitoring and logging
- Shared cost allocation
- Single pane of glass for operations

## Cross-Resource Group Permissions

The deployment automatically configures RBAC across resource groups:

| From | To | Role | Purpose |
|------|-----|------|---------|
| App Service | Cosmos DB | Cosmos DB Data Contributor | Read/write parcel data |
| App Service | Azure OpenAI | Cognitive Services OpenAI User | Call AI agents |
| App Service | Speech Service | Cognitive Services User | Voice features |
| App Service | Vision Service | Cognitive Services User | OCR/image analysis |
| AI Hub | Azure OpenAI | Cognitive Services OpenAI User | Train/deploy models |
| AI Project | Azure OpenAI | Cognitive Services OpenAI User | Agent inference |

## Deployment

### New Deployment

The deployment now operates at **subscription scope** (not resource group scope):

```powershell
# Deploy all infrastructure (creates 4 resource groups)
.\deploy_to_azure.ps1

# With custom environment
.\deploy_to_azure.ps1 -Environment "staging" -Sku "B3"
```

### What Happens During Deployment

1. **Resource Groups Created** (4 groups)
2. **Shared Services Deployed** (Log Analytics first)
3. **Frontend Deployed** (App Insights uses Log Analytics)
4. **Middleware Deployed** (AI Hub uses App Insights)
5. **Backend Deployed** (Cosmos DB independent)
6. **RBAC Configured** (cross-RG permissions)
7. **App Settings Updated** (endpoints from all RGs)

### Parameters

The script no longer requires `-ResourceGroup` parameter:

```powershell
# Old way (single RG)
.\deploy_to_azure.ps1 -ResourceGroup "RG-Zava-Logistics"

# New way (multi-RG, auto-named)
.\deploy_to_azure.ps1 -Environment "dev"  # Creates 4 RGs automatically
```

## Bicep Template Structure

```
infra/
├── main.bicep                      # Subscription-scope orchestrator
└── modules/
    ├── frontend.bicep              # App Service resources
    ├── middleware.bicep            # AI services
    ├── backend.bicep               # Cosmos DB
    ├── shared.bicep                # Maps, Speech, Vision, Logs
    └── rbac/
        └── cognitiveServicesUser.bicep  # Reusable RBAC module
```

### Module Dependencies

```
shared.bicep (Log Analytics)
    ↓
frontend.bicep (App Insights needs Log Analytics)
    ↓
middleware.bicep (AI Hub needs App Insights)

backend.bicep (independent)
```

## Benefits

### Security
- **Principle of Least Privilege**: Each RG has narrowly scoped permissions
- **Defense in Depth**: Compromise of one RG doesn't affect others
- **Audit Trail**: Resource group-level activity logs

### Operations
- **Independent Scaling**: Scale web tier without affecting database
- **Isolated Updates**: Update AI models without app downtime
- **Granular Monitoring**: Per-RG cost tracking and alerts

### Development
- **Team Boundaries**: Frontend, AI, Backend teams have separate RGs
- **Safe Experimentation**: Test changes in middleware RG without risk to production data
- **Parallel Development**: Multiple teams can work simultaneously

### Compliance
- **Data Residency**: Backend RG can be deployed in specific regions
- **Access Control**: Separate RGs simplify compliance audits
- **Retention Policies**: Different backup policies per RG

## Cost Tracking

Each resource group can have separate cost tags and budgets:

```bash
# View costs by resource group
az consumption usage list --start-date 2026-03-01

# Frontend costs (web hosting)
az cost management query --scope /subscriptions/{id}/resourceGroups/RG-Zava-Frontend-dev

# Middleware costs (AI inference)
az cost management query --scope /subscriptions/{id}/resourceGroups/RG-Zava-Middleware-dev

# Backend costs (data storage)
az cost management query --scope /subscriptions/{id}/resourceGroups/RG-Zava-Backend-dev

# Shared costs (allocated across apps)
az cost management query --scope /subscriptions/{id}/resourceGroups/RG-Zava-Shared-dev
```

## Troubleshooting

### "Deployment at subscription scope failed"

Check that you have subscription-level permissions:
```bash
az role assignment create --assignee <your-email> --role "Contributor" --scope /subscriptions/<subscription-id>
```

### "Cross-resource group RBAC not working"

RBAC permissions take 2-5 minutes to propagate. The deployment script waits 60 seconds, but you may need to wait longer.

### "Cannot find output property"

The outputs are now nested. Update your scripts:

```powershell
# Old
$appServiceName = $bicepOutput.appServiceName.value

# New
$appServiceName = $bicepOutput.frontend.value.appServiceName
$cosmosEndpoint = $bicepOutput.backend.value.cosmosDbEndpoint
$openAIEndpoint = $bicepOutput.middleware.value.openAIServiceEndpoint
```

## Migration from Single RG

If you have an existing deployment in a single resource group:

1. **Backup existing data** (export Cosmos DB)
2. **Delete old deployment** (or keep running in parallel)
3. **Run new deployment** with multi-RG architecture
4. **Restore data** to new Cosmos DB
5. **Update DNS/custom domains** to point to new App Service

## Future Enhancements

Potential improvements to the architecture:

- **Virtual Network Integration**: Place resources in VNets per RG
- **Private Endpoints**: Secure cross-RG communication
- **Azure Front Door**: Multi-region frontend distribution
- **Geo-Replication**: Replicate Cosmos DB across regions
- **Key Vault**: Centralize secrets in Shared RG
- **API Management**: API gateway in middleware RG

---

**Last Updated:** March 25, 2026  
**Author:** GitHub Copilot  
**Related:** [AGENTS.md](../AGENTS.md), [DEPLOYMENT.md](DEPLOYMENT.md)
