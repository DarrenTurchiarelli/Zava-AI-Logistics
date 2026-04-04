# GitHub Actions & CI/CD Workflows

This folder contains GitHub Actions workflows for automated testing, deployment, and CI/CD pipelines for the Zava Logistics platform.

## 📋 Available Workflows

### 1. Deploy Infrastructure & Application (Hybrid) 🚀
**File:** [`workflows/deploy-infrastructure.yml`](workflows/deploy-infrastructure.yml)  
**Trigger:** Manual (workflow_dispatch)  
**Purpose:** Complete infrastructure + application deployment using PowerShell script

**What it does:**
- ✅ Authenticates with Azure (keyless OIDC)
- ✅ Runs the proven `deploy_to_azure.ps1` script
- ✅ Deploys all infrastructure (Bicep templates)
- ✅ Creates 9 Azure OpenAI agents
- ✅ Deploys application code
- ✅ Generates 2500 demo parcels automatically
- ✅ Configures RBAC permissions
- ✅ Uploads deployment artifacts

**Duration:** ~15-20 minutes

**When to use:**
- First-time deployment to Azure
- Complete infrastructure recreation
- Full deployment with agents and demo data
- Production deployments

**Parameters:**
- `resource_group` - Custom RG name (optional)
- `location` - Azure region (default: australiaeast)
- `sku` - App Service tier (default: B2)

**Setup Required:** See [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)

---

### 2. Deploy Application Code Only
**File:** [`workflows/deploy-azure.yml`](workflows/deploy-azure.yml)  
**Trigger:** Push to main, Manual  
**Purpose:** Code deployment only (assumes infrastructure exists)

**What it does:**
- ✅ Validates agent configuration
- ✅ Runs tests
- ✅ Deploys code to existing App Service
- ✅ Updates app settings
- ✅ Optionally updates agents

**Duration:** ~5-10 minutes

**When to use:**
- Code updates only
- Bug fixes
- Feature deployments (infrastructure unchanged)
- Quick iterations

**Setup Required:** 
- Existing Azure infrastructure
- Agent IDs in GitHub secrets

---

### 3. Test & Lint
**File:** [`workflows/test.yml`](workflows/test.yml)  
**Trigger:** Push, Pull Request, Manual  
**Purpose:** Automated testing and code quality checks

**What it does:**
- ✅ Runs pytest on Python 3.11 & 3.12
- ✅ Validates import paths
- ✅ Checks code quality
- ✅ Fast feedback on PRs

**Duration:** ~2-3 minutes

**When to use:**
- Automatically runs on every push
- Required for PR reviews
- Local testing validation

---

## 🔧 Setup Guides

### For First-Time Setup
📖 **[GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)** - Complete setup guide
- Azure Service Principal creation (OIDC)
- Federated credentials configuration
- GitHub secrets setup
- Troubleshooting common issues

✅ **[PREFLIGHT_CHECKLIST.md](PREFLIGHT_CHECKLIST.md)** - Pre-deployment validation checklist
- Step-by-step verification before first deployment
- Azure subscription validation
- Cost awareness and SKU selection
- Post-deployment checklist

### Quick Reference
📘 **[GITHUB_ACTIONS_QUICK_REFERENCE.md](GITHUB_ACTIONS_QUICK_REFERENCE.md)** - Quick commands and scenarios
- Running deployments via UI or CLI
- Monitoring deployment status
- Common deployment scenarios
- Cost estimates
- Best practices

---

## 🚀 Quick Start

### Deploy Complete Infrastructure (Recommended First Time)
1. Complete setup: [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)
2. Go to **Actions** → **Deploy Infrastructure & Application**
3. Click **Run workflow** → Use defaults
4. ⏱️ Wait 15-20 minutes
5. Check deployment summary for app URL

### Deploy Code Update (After Infrastructure Exists)
1. Make code changes
2. Push to `main` branch
3. Workflow auto-triggers
4. Or: **Actions** → **Deploy Application Code Only** → **Run workflow**

### Run Tests
- Automatically runs on push/PR
- Manual: **Actions** → **Test & Lint** → **Run workflow**

---

## 🔐 Required GitHub Secrets

### Azure Authentication (OIDC - Keyless)
| Secret | Description | How to Get |
|--------|-------------|------------|
| `AZURE_CLIENT_ID` | Service Principal App ID | See setup guide |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | `az account show` |
| `AZURE_SUBSCRIPTION_ID` | Target subscription | `az account show` |

### Agent IDs (Created by Infrastructure Workflow)
| Secret | Description |
|--------|-------------|
| `CUSTOMER_SERVICE_AGENT_ID` | Customer service agent |
| `FRAUD_RISK_AGENT_ID` | Fraud detection agent |
| `IDENTITY_AGENT_ID` | Identity verification agent |
| `DISPATCHER_AGENT_ID` | Parcel dispatcher agent |
| `PARCEL_INTAKE_AGENT_ID` | Parcel intake agent |
| `SORTING_FACILITY_AGENT_ID` | Sorting facility agent |
| `DELIVERY_COORDINATION_AGENT_ID` | Delivery coordination agent |
| `OPTIMIZATION_AGENT_ID` | Optimization agent |

### Azure Resources (Set by Infrastructure Workflow)
| Secret | Description |
|--------|-------------|
| `AZURE_AI_PROJECT_ENDPOINT` | AI Foundry endpoint |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | OpenAI model name |
| `COSMOS_DB_ENDPOINT` | Cosmos DB endpoint |
| `COSMOS_DB_DATABASE_NAME` | Database name |
| `AZURE_RESOURCE_GROUP` | Main resource group |
| `AZURE_WEBAPP_NAME` | App Service name |

---

## 📊 Workflow Comparison

| Feature | Infrastructure Workflow | Code-Only Workflow | Test Workflow |
|---------|------------------------|-------------------|---------------|
| **Trigger** | Manual only | Push + Manual | Push/PR + Manual |
| **Duration** | 15-20 min | 5-10 min | 2-3 min |
| **Creates Infrastructure** | ✅ Yes | ❌ No | ❌ No |
| **Creates Agents** | ✅ Yes | ⚠️ Optional | ❌ No |
| **Deploys Code** | ✅ Yes | ✅ Yes | ❌ No |
| **Generates Demo Data** | ✅ Yes (2500 parcels) | ❌ No | ❌ No |
| **Runs Tests** | ❌ No | ✅ Yes | ✅ Yes |
| **Cost** | Free (2000 min/mo) | Free | Free |

---

## 🎯 Recommended Workflow

### First-Time Deployment
```
1. Setup → Follow GITHUB_ACTIONS_SETUP.md
2. Infrastructure Workflow → Create everything
3. Test → Login at deployed URL (admin/admin123)
4. Iterate → Use Code-Only Workflow for updates
```

### Development Cycle
```
1. Make changes locally
2. Test Workflow → Auto-runs on push
3. Code-Only Workflow → Deploy to dev/staging
4. Manual approval → Deploy to production
```

### Production Deployment
```
1. Enable environment protection (Settings → Environments)
2. Add required reviewers
3. Infrastructure Workflow → With production SKU (P1V2+)
4. Monitor → Check deployment artifacts
```

---

## 🐛 Troubleshooting

### "Failed to login to Azure"
- **Cause:** OIDC not configured
- **Fix:** Re-check federated credentials (step 2 in setup guide)
- **Verify:** `az ad app federated-credential list --id <client-id>`

### "Insufficient permissions"
- **Cause:** Service principal lacks roles
- **Fix:** Re-grant Contributor + RBAC Admin roles
- **Command:** See setup guide step 1

### "Agent creation failed"
- **Cause:** Import path errors (v2.0 restructuring)
- **Fix:** Ensure scripts use `src.infrastructure.agents.*` imports
- **Verify:** Run `python scripts/create_foundry_agents_openai.py` locally

### Workflow taking too long
- **Infrastructure:** Normal (15-20 min)
- **Code-Only:** Should be 5-10 min
- **Tests:** Should be 2-3 min
- **If stuck:** Check workflow logs for specific step

---

## 💡 Best Practices

### Branch Protection
- ✅ Require PR reviews before merge
- ✅ Require status checks (tests must pass)
- ✅ Restrict direct pushes to `main`

### Environment Protection
- ✅ Create `production` environment
- ✅ Add required reviewers (1-2 people)
- ✅ Optional: Wait timer (5-10 min)

### Secrets Management
- ✅ Use OIDC (no passwords stored)
- ✅ Rotate secrets quarterly
- ✅ Use separate subscriptions for dev/prod

### Cost Management
- ✅ Use B1/B2 SKUs for dev/test
- ✅ Use P1V2+ for production
- ✅ Monitor GitHub Actions minutes
- ✅ Delete dev resources when not in use

---

## 📚 Additional Resources

- [Main Project README](../README.md)
- [AGENTS.md](../AGENTS.md) - AI agent documentation
- [AZURE_DEPLOYMENT.md](../docs/AZURE_DEPLOYMENT.md) - Detailed deployment guide
- [PowerShell Script](../deploy_to_azure.ps1) - The script workflows run

---

## 🆘 Support

- **Workflow issues:** Check logs in Actions tab
- **Azure errors:** Review [AZURE_DEPLOYMENT.md](../docs/AZURE_DEPLOYMENT.md)
- **Local testing:** Run `.\deploy_to_azure.ps1` directly
- **Agent issues:** See [AGENTS.md](../AGENTS.md)

---

**Last Updated:** April 3, 2026  
**Maintained By:** Darren Turchiarelli (Microsoft Australia)
