# Managed Identity Authentication

Zava uses **Azure Managed Identity exclusively** for all runtime operations. No API keys or connection strings are stored in environment variables or configuration files.

## Authentication Overview

### ✅ Managed Identity (Production)
All Azure services authenticate using system-assigned managed identities:
- **Azure Cosmos DB**: App Service → Cosmos DB (Data Contributor role)
- **Azure OpenAI**: App Service → OpenAI (OpenAI User role)
- **Azure Speech Services**: App Service → Speech (Cognitive Services User role)
- **Azure Computer Vision**: App Service → Vision (Cognitive Services User role)
- **Azure AI Hub/Project**: App Service → AI Hub (OpenAI User role)

### 🔐 Security Benefits
- **No secrets in code**: Zero API keys, connection strings, or passwords in environment variables
- **Automatic credential rotation**: Azure handles credential lifecycle
- **Least privilege**: Each service has only the permissions it needs
- **Audit trail**: All operations logged in Azure Activity Log

## Deployment Process

### Azure OpenAI Agent Creation
The **only exception** is during agent creation at deployment time:

1. **Before agent creation** (30 seconds):
   - Deployment script temporarily enables API key authentication on Azure OpenAI
   - Retrieves API key for agent creation
   - Creates 8 AI agents via Azure OpenAI Assistants API

2. **After agent creation** (immediately):
   - Deployment script disables API key authentication
   - Azure OpenAI switches back to managed identity only
   - API key is discarded (not stored anywhere)

**Total API key exposure**: ~30-60 seconds during deployment only.

## Runtime Operations

### Application Code
All application code uses `DefaultAzureCredential` (local) or `ManagedIdentityCredential` (Azure):

```python
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.ai.projects import AIProjectClient

# Automatically uses managed identity in Azure
credential = DefaultAzureCredential()
client = AIProjectClient(endpoint=AZURE_AI_PROJECT_ENDPOINT, credential=credential)
```

### No Keys in Environment Variables
The `.env` file and App Service settings contain **zero secrets**:

```bash
# ✅ SAFE - No keys
AZURE_AI_PROJECT_ENDPOINT=https://...
COSMOS_DB_ENDPOINT=https://...
CUSTOMER_SERVICE_AGENT_ID=asst_xxx

# ❌ NEVER SET THESE (they don't exist in production)
# AZURE_OPENAI_API_KEY=xxx
# COSMOS_CONNECTION_STRING=xxx
```

## Infrastructure Configuration

### Bicep Template (infra/main.bicep)
All services have `disableLocalAuth: true` by default:

```bicep
resource openAIService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  properties: {
    disableLocalAuth: true  // Managed identity only
  }
}

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  properties: {
    disableLocalAuth: true  // Force RBAC authentication only
  }
}
```

### RBAC Role Assignments
Automatic role assignments in Bicep:

```bicep
// Cosmos DB Data Contributor for App Service
resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = {
  properties: {
    roleDefinitionId: '${cosmosDbAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: appService.identity.principalId
  }
}

// Cognitive Services OpenAI User for App Service
resource openAIRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: appService.identity.principalId
  }
}
```

## Local Development

### Azure CLI Authentication
Local development uses Azure CLI credentials:

```bash
# Login to Azure
az login

# Application automatically uses your Azure identity
python app.py
```

### No .env Keys Required
Local `.env` contains only endpoints:

```bash
AZURE_AI_PROJECT_ENDPOINT=https://...
COSMOS_DB_ENDPOINT=https://...
```

## Troubleshooting

### "Authentication Failed" Errors

**Root Cause**: RBAC permissions take 2-5 minutes to propagate after deployment.

**Solution**: Wait a few minutes, then restart the app:

```bash
az webapp restart --name <webapp-name> --resource-group RG-Zava-Logistics
```

### "Forbidden" or "Access Denied" Errors

**Check RBAC Assignments**:
```bash
# Check Cosmos DB role assignments
az role assignment list --scope <cosmos-resource-id> --query "[].{principal:principalName,role:roleDefinitionName}"

# Check OpenAI role assignments
az role assignment list --scope <openai-resource-id> --query "[].{principal:principalName,role:roleDefinitionName}"
```

**Verify Managed Identity**:
```bash
# Get app service principal ID
az webapp identity show --name <webapp-name> --resource-group RG-Zava-Logistics --query principalId
```

### Local Development Connection Issues

**Solution**: Login to Azure CLI with the correct account:

```bash
# Check current account
az account show

# Switch subscription if needed
az account set --subscription <subscription-id>

# Re-login if necessary
az login
```

## Compliance & Best Practices

### ✅ Follows Azure Well-Architected Framework
- **Security**: Zero secrets in code or configuration
- **Reliability**: Automatic credential rotation
- **Operational Excellence**: Centralized identity management
- **Performance**: No additional latency

### ✅ Meets Security Standards
- **NIST Cybersecurity Framework**: Identity verification and authorization
- **ISO 27001**: Access control and authentication
- **GDPR**: Data access controls and audit logging

### ✅ Microsoft Security Best Practices
- [Azure AD Managed Identities Best Practices](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/managed-identity-best-practice-recommendations)
- [Passwordless Connections](https://learn.microsoft.com/azure/developer/intro/passwordless-overview)

## Related Documentation

- [Azure Deployment Guide](AZURE_DEPLOYMENT.md)
- [Security Policy](../SECURITY.md)
- [AGENTS.md - Deployment Script Actions](../AGENTS.md#deployment-script-actions)

---

**Last Updated**: March 25, 2026  
**Security Model**: Managed Identity Only (Zero Secrets)  
**Maintained By**: Darren Turchiarelli (Microsoft Australia)
