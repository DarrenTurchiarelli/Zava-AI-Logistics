# GitHub Actions Pre-Flight Checklist

Use this checklist before running your first GitHub Actions deployment to ensure everything is configured correctly.

## ✅ Pre-Deployment Checklist

### 1. Azure Service Principal (OIDC)
- [ ] Created Azure AD App Registration
- [ ] Created Service Principal from App Registration
- [ ] Noted down Client ID (App ID)
- [ ] Assigned **Contributor** role at subscription level
- [ ] Assigned **Role Based Access Control Administrator** role at subscription level
- [ ] Created federated credential for `main` branch
- [ ] Verified federated credential subject: `repo:YOUR_ORG/Zava-Logistics:ref:refs/heads/main`

**Command to verify:**
```powershell
$clientId = "your-client-id"
az ad app federated-credential list --id $clientId
```

---

### 2. GitHub Secrets Configured
Navigate to: **Settings** → **Secrets and variables** → **Actions**

#### Required for All Workflows:
- [ ] `AZURE_CLIENT_ID` - Service Principal Client ID
- [ ] `AZURE_TENANT_ID` - Azure AD Tenant ID  
- [ ] `AZURE_SUBSCRIPTION_ID` - Target Azure subscription

**Command to get values:**
```powershell
az account show --query "{tenantId:tenantId, subscriptionId:id}"
```

#### Optional (Created by Infrastructure Workflow):
- [ ] `AZURE_WEBAPP_NAME` - Will be set after first deployment
- [ ] `AZURE_RESOURCE_GROUP` - Will be set after first deployment
- [ ] Agent IDs (8 secrets) - Will be set after agent creation

---

### 3. Repository Settings
- [ ] Repository is not archived
- [ ] GitHub Actions are enabled (Settings → Actions → General)
- [ ] Workflow permissions: "Read and write permissions" (Settings → Actions → General → Workflow permissions)

---

### 4. Local Prerequisites (For Testing)
- [ ] Python 3.11+ installed
- [ ] Requirements.txt dependencies installed
- [ ] Azure CLI installed
- [ ] Logged in with `az login`
- [ ] Script imports fixed (v2.0 structure: `src.infrastructure.agents.*`)

**Quick test:**
```powershell
python -c "from src.infrastructure.agents.core.prompt_loader import get_agent_prompt; print('✅ Imports work')"
```

---

### 5. Azure Subscription Validation
- [ ] Subscription is active (not disabled/expired)
- [ ] Have sufficient quota for resources:
  - [ ] App Service Plan (1x B2 or higher)
  - [ ] Cosmos DB account (1x)
  - [ ] Azure OpenAI service (1x)
  - [ ] Azure AI Hub (1x)
  - [ ] Azure AI Project (1x)
  - [ ] Cognitive Services (Speech, Vision, Maps)
- [ ] No naming conflicts with existing resources in subscription

**Command to check quota:**
```powershell
az vm list-usage --location australiaeast -o table
```

---

### 6. Cost Awareness
- [ ] Understand GitHub Actions usage limits:
  - Public repos: **Unlimited free minutes**
  - Private repos: **2000 free minutes/month**, then $0.008/min
- [ ] Understand Azure costs:
  - Dev/Test (B1): ~$15/month
  - Production (B2): ~$30/month
  - Premium (P1V2): ~$150/month
  - Plus: Cosmos DB (~$25), OpenAI (pay-per-use), Storage (<$5)

---

### 7. First Deployment Parameters
Decision checklist:

- [ ] **Resource Group Name:**
  - [ ] Use default (auto-generated `RG-Zava-*`)
  - [ ] Use custom name: ________________

- [ ] **Azure Region:**
  - [ ] Use default `australiaeast`
  - [ ] Use different region: ________________

- [ ] **App Service SKU:**
  - [ ] Use default `B2` (recommended)
  - [ ] Use cheaper `B1` (dev/test only)
  - [ ] Use production `P1V2` or higher

---

## 🚀 Ready to Deploy?

### Final Verification Commands

Run these to verify everything before deployment:

```powershell
# 1. Verify Azure authentication
az account show

# 2. Verify service principal has correct roles
$clientId = "your-client-id"
$subscriptionId = "your-subscription-id"
az role assignment list --assignee $clientId --scope "/subscriptions/$subscriptionId" -o table

# 3. Verify GitHub secrets exist (from repository settings UI)
# Go to: Settings → Secrets and variables → Actions

# 4. Test Python imports
python -c "from src.infrastructure.agents.core.prompt_loader import get_agent_prompt; print('✅')"
python -c "from src.infrastructure.agents.tools.cosmos_tools import AGENT_TOOLS; print('✅')"
```

### Start Deployment

1. Go to: https://github.com/YOUR_ORG/Zava-Logistics/actions
2. Click: **Deploy Infrastructure & Application (PowerShell)**
3. Click: **Run workflow**
4. Select branch: `main`
5. Configure parameters (or use defaults)
6. Click: **Run workflow**
7. ⏱️ Wait 15-20 minutes
8. ✅ Check deployment summary

---

## ❌ Troubleshooting Before You Start

### "I don't have Azure CLI installed"
```powershell
# Windows: Install via winget
winget install Microsoft.AzureCLI

# Or download from: https://aka.ms/installazurecliwindows
```

### "I don't have the right Azure permissions"
You need:
- Subscription Owner role, OR
- Subscription Contributor + User Access Administrator, OR
- Subscription Contributor + Role Based Access Control Administrator

Ask your Azure admin if you don't have these.

### "I don't know my subscription ID"
```powershell
az login
az account show --query id -o tsv
```

### "I already have resources with the same names"
Either:
- Delete existing resources first, OR
- Use custom resource group name in workflow parameters, OR
- Deploy to a different Azure subscription

### "Git push fails or Actions tab is missing"
Check:
- Repository Settings → Actions → General → Actions permissions
- Set to: "Allow all actions and reusable workflows"

---

## 📋 Post-Deployment Checklist

After your first successful deployment:

- [ ] Deployment completed successfully (check workflow logs)
- [ ] Received deployment summary with app URL
- [ ] Can access app at: `https://<webapp-name>.azurewebsites.net`
- [ ] Can login with admin/admin123
- [ ] Downloaded deployment artifacts (`.azure-deployment.json`)
- [ ] All 9 agents created (check workflow output)
- [ ] Demo data generated (2500 parcels)
- [ ] Saved agent IDs to GitHub secrets (optional, for code-only workflow)

---

## 🎯 Next Steps After First Deployment

1. **Test the application:**
   - Login with admin/admin123
   - Try tracking a parcel: RG857954
   - Test voice chat feature
   - Check dispatcher page

2. **Update GitHub secrets with agent IDs:**
   - Copy agent IDs from `.azure-deployment.json`
   - Add to GitHub secrets
   - Enables code-only deployment workflow

3. **Set up environment protection:**
   - Settings → Environments → New environment: `production`
   - Add required reviewers
   - Prevents accidental deployments

4. **Plan your development workflow:**
   - Use Infrastructure workflow for full deployments
   - Use Code-Only workflow for updates
   - Enable branch protection on `main`

---

## 🆘 Need Help?

- **Setup issues:** [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)
- **Workflow reference:** [GITHUB_ACTIONS_QUICK_REFERENCE.md](GITHUB_ACTIONS_QUICK_REFERENCE.md)
- **All workflows:** [README.md](README.md)
- **Azure deployment:** [../docs/AZURE_DEPLOYMENT.md](../docs/AZURE_DEPLOYMENT.md)

---

**Last Updated:** April 3, 2026  
**Estimated Setup Time:** 20-30 minutes (first time)  
**Estimated Deployment Time:** 15-20 minutes (via GitHub Actions)
