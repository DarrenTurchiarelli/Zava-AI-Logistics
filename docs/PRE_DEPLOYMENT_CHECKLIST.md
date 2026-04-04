# Pre-Deployment Checklist

Quick reference for deploying Zava Logistics to Azure.

## Before Running `.\deploy_to_azure.ps1`

### ✅ Automated Preflight Check
```powershell
# Run the preflight check script
.\scripts\preflight_check.ps1

# For detailed output
.\scripts\preflight_check.ps1 -Verbose
```

---

## What Gets Checked

### 1. Azure CLI & Authentication
- ✓ Azure CLI installed (version 2.48.1+)
- ✓ Logged into Azure (`az login`)
- ✓ Subscription selected

### 2. Python Environment  
- ✓ Python 3.11+ installed
- ✓ All required packages installed (`pip install -r requirements.txt`)
  - flask
  - azure-cosmos
  - azure-identity
  - openai
  - pydantic

### 3. Environment Configuration
- ✓ `.env.example` exists (template)
- ✓ `.env` file created (copy from .env.example)
- ⚠ Environment variables configured:
  - `COSMOS_DB_DATABASE_NAME=logisticstracking`
  - `AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o`

### 4. Project Structure
- ✓ All critical folders exist:
  - `src/infrastructure/agents/skills/` (agent prompts)
  - `src/interfaces/web/routes/` (Flask blueprints)
  - `src/domain/models/` (domain models)
  - `infra/` (Bicep templates)
  - `scripts/` (deployment scripts)

### 5. Agent Skills Validation
- ✓ All 9 agent skill folders exist
- ✓ All `system-prompt.md` files loadable
- ✓ Prompts ready for Azure AI Foundry registration

### 6. Deployment Scripts
- ✓ `deploy_to_azure.ps1` exists
- ✓ `scripts/create_foundry_agents_openai.py` exists
- ✓ `scripts/register_agent_tools_openai.py` exists
- ✓ `scripts/initialize_all_containers.py` exists

### 7. Infrastructure Templates
- ✓ `infra/main.bicep` exists
- ✓ Bicep CLI installed (`az bicep install`)
- ✓ Bicep template validates without errors

### 8. Git Repository
- ⚠ Uncommitted changes (expected after restructuring)
- ✓ Working tree tracked

### 9. Application
- ✓ Flask app imports successfully
- ✓ No Python syntax errors

---

## Manual Pre-Flight Tasks

### 1. Install Prerequisites
```powershell
# Azure CLI
winget install Microsoft.AzureCLI

# Python 3.11+
winget install Python.Python.3.11

# Bicep (via Azure CLI)
az bicep install
```

### 2. Login to Azure
```powershell
az login

# Verify subscription
az account show

# Change subscription if needed
az account set --subscription "Your-Subscription-Name"
```

### 3. Install Python Dependencies
```powershell
# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment
```powershell
# Copy template
Copy-Item .env.example .env

# Edit .env file (optional for deployment, required for local dev)
# The deployment script will set most values automatically
code .env
```

**Note**: For deployment, you only need these set:
- `COSMOS_DB_DATABASE_NAME=logisticstracking`
- `AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o`

All other values (endpoints, keys, agent IDs) are set automatically by the deployment script.

---

## Warnings You Can Ignore

### ⚠ Environment Variables Not Configured
- **What**: `.env` file has placeholder values
- **Why**: Deployment script fills these automatically from Azure resources
- **Action**: ✅ Safe to proceed

### ⚠ Uncommitted Git Changes
- **What**: 90+ files changed from restructuring
- **Why**: You just completed the enterprise restructuring
- **Action**: ✅ Safe to proceed (commit after successful deployment)

---

## Critical Blockers (Must Fix)

### ❌ Azure CLI Not Authenticated
```powershell
az login
```

### ❌ Python Not Installed or Wrong Version
```powershell
winget install Python.Python.3.11
```

### ❌ Missing Python Packages
```powershell
pip install -r requirements.txt
```

### ❌ Bicep Template Errors
```powershell
# Check errors
bicep build infra/main.bicep

# Fix errors in bicep files, then re-run preflight
.\scripts\preflight_check.ps1
```

### ❌ Agent Skills Validation Failed
```powershell
# Test validation directly
python scripts/validate_agent_skills.py

# Check for missing files in src/infrastructure/agents/skills/
```

---

## Ready to Deploy?

### ✅ All Checks Pass
```powershell
# Deploy to Azure
.\deploy_to_azure.ps1

# Or with custom parameters
.\deploy_to_azure.ps1 -Location "australiaeast" -Environment "dev" -Sku "B3"
```

### ⚠ Warnings Only (No Failures)
```powershell
# Safe to proceed - warnings are informational
.\deploy_to_azure.ps1
```

### ❌ Any Failures
```powershell
# Fix failures first, then re-run preflight
.\scripts\preflight_check.ps1 -Verbose

# After fixing, deploy
.\deploy_to_azure.ps1
```

---

## Post-Deployment

After successful deployment, the script will:
1. ✅ Create all Azure resources (4 resource groups)
2. ✅ Deploy infrastructure (Cosmos DB, AI Hub, OpenAI, Maps, etc.)
3. ✅ Create all 9 AI agents in Azure AI Foundry
4. ✅ Register tools with Customer Service Agent
5. ✅ Deploy application code
6. ✅ Initialize database containers
7. ✅ Create demo users
8. ✅ Generate demo data

**Test the deployment:**
```powershell
# Get the app URL from deployment output
# Example: https://zava-dev-app-abc123.azurewebsites.net

# Or find it in Azure Portal
az webapp show --name <webapp-name> --resource-group RG-Zava-Frontend-dev --query defaultHostName -o tsv
```

---

## Troubleshooting

### Preflight Check Fails with Import Error
```powershell
# Ensure you're in the project root
cd C:\Workbench\lastmile

# Verify Python can import
python -c "from src.interfaces.web.app import create_app; print('OK')"
```

### Bicep Build Fails
```powershell
# Check for syntax errors
bicep build infra/main.bicep

# Ensure Bicep is up to date
az bicep upgrade
```

### Agent Validation Fails
```powershell
# Run validation to see specific errors
python scripts/validate_agent_skills.py

# Check that skills folder exists
Test-Path src/infrastructure/agents/skills
```

---

**Last Updated**: April 3, 2026  
**Script Location**: `scripts/preflight_check.ps1`  
**Documentation**: `docs/AZURE_DEPLOYMENT.md`
