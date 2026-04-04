# GitHub Actions Setup Guide

This guide explains how to configure GitHub Actions to run the PowerShell deployment script with Azure authentication.

## Overview

The `deploy-infrastructure.yml` workflow implements a **hybrid approach**:
- ✅ **Version controlled** - Track all deployments in Git history
- ✅ **Audit trail** - Know who deployed what and when
- ✅ **Consistent environment** - Same Python version every time
- ✅ **Manual trigger** - Deploy on-demand with custom parameters
- ✅ **Existing logic** - Runs your proven PowerShell script

## Prerequisites

- Azure subscription with Owner or Contributor + RBAC Administrator access
- GitHub repository with this codebase
- Azure CLI installed locally (for setup)

## Setup Steps

### 1. Create Azure Service Principal with OIDC

Azure OIDC (OpenID Connect) provides keyless authentication - no secrets to rotate or leak.

```powershell
# Set your values
$subscriptionId = "your-subscription-id"
$appName = "github-zava-logistics-deploy"

# Login to Azure
az login
az account set --subscription $subscriptionId

# Create app registration
$appId = az ad app create --display-name $appName --query appId -o tsv
Write-Host "App ID (Client ID): $appId"

# Create service principal
$servicePrincipalId = az ad sp create --id $appId --query id -o tsv
Write-Host "Service Principal ID: $servicePrincipalId"

# Assign Contributor role at subscription level
az role assignment create `
    --assignee $appId `
    --role Contributor `
    --scope "/subscriptions/$subscriptionId"

# Assign RBAC Administrator role (needed for assigning roles to managed identities)
az role assignment create `
    --assignee $appId `
    --role "Role Based Access Control Administrator" `
    --scope "/subscriptions/$subscriptionId"

Write-Host "✓ Service Principal created with Contributor + RBAC Admin roles"
```

### 2. Configure Federated Credentials (OIDC)

This allows GitHub Actions to authenticate without storing secrets.

```powershell
# Set your GitHub repository details
$githubOrg = "your-github-username"  # e.g., "DarrenTurchiarelli"
$githubRepo = "Zava-Logistics"
$githubBranch = "main"

# Create federated credential for main branch
az ad app federated-credential create `
    --id $appId `
    --parameters "{
        `"name`": `"github-$githubRepo-main`",
        `"issuer`": `"https://token.actions.githubusercontent.com`",
        `"subject`": `"repo:$githubOrg/${githubRepo}:ref:refs/heads/$githubBranch`",
        `"audiences`": [`"api://AzureADTokenExchange`"]
    }"

Write-Host "✓ Federated credential created for main branch"
```

**Optional: Add credential for pull requests (if you want to test deployments from PRs)**
```powershell
az ad app federated-credential create `
    --id $appId `
    --parameters "{
        `"name`": `"github-$githubRepo-pr`",
        `"issuer`": `"https://token.actions.githubusercontent.com`",
        `"subject`": `"repo:$githubOrg/${githubRepo}:pull_request`",
        `"audiences`": [`"api://AzureADTokenExchange`"]
    }"
```

### 3. Get Required Values

```powershell
# You'll need these for GitHub Secrets
$tenantId = az account show --query tenantId -o tsv
$subscriptionId = az account show --query id -o tsv
$clientId = $appId  # Same as App ID from step 1

Write-Host ""
Write-Host "========================================"
Write-Host "GitHub Secrets Configuration"
Write-Host "========================================"
Write-Host "AZURE_CLIENT_ID: $clientId"
Write-Host "AZURE_TENANT_ID: $tenantId"
Write-Host "AZURE_SUBSCRIPTION_ID: $subscriptionId"
Write-Host ""
Write-Host "Add these to: GitHub → Settings → Secrets and variables → Actions"
```

### 4. Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add each of these:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AZURE_CLIENT_ID` | `<appId from step 1>` | Service principal application ID |
| `AZURE_TENANT_ID` | `<tenantId from step 3>` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `<subscriptionId from step 3>` | Target Azure subscription |

**Security Note**: With OIDC, you don't store any passwords or keys in GitHub - just IDs.

### 5. Verify Setup

Test the workflow:

1. Go to: **Actions** → **Deploy Infrastructure & Application (PowerShell)**
2. Click **Run workflow**
3. Select branch: `main`
4. (Optional) Customize parameters or use defaults
5. Click **Run workflow**

The workflow will:
- ✅ Authenticate with Azure (keyless)
- ✅ Install Python dependencies
- ✅ Run `deploy_to_azure.ps1`
- ✅ Upload deployment config as artifact

Expected duration: **15-20 minutes**

## Workflow Parameters

When manually triggering the workflow, you can customize:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resource_group` | Custom resource group name | `RG-Zava-*` (auto-generated) |
| `location` | Azure region | `australiaeast` |
| `sku` | App Service plan tier | `B2` |

## Troubleshooting

### "Failed to login to Azure" Error

**Cause**: Federated credential not configured correctly

**Fix**:
```powershell
# Verify federated credentials exist
az ad app federated-credential list --id $appId

# Ensure subject matches your repository EXACTLY
# Format: repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/main
```

### "Insufficient permissions" Error

**Cause**: Service principal lacks required roles

**Fix**:
```powershell
# Re-add roles (replace $subscriptionId and $appId)
az role assignment create --assignee $appId --role Contributor --scope "/subscriptions/$subscriptionId"
az role assignment create --assignee $appId --role "Role Based Access Control Administrator" --scope "/subscriptions/$subscriptionId"
```

### "Timeout after 60 minutes"

**Cause**: Deployment taking longer than expected

**Fix**: Increase timeout in `.github/workflows/deploy-infrastructure.yml`:
```yaml
jobs:
  deploy-infrastructure:
    timeout-minutes: 90  # Increase from 60 to 90
```

### "Python dependencies failed to install"

**Cause**: requirements.txt issue or network timeout

**Fix**: Check workflow logs for specific package errors. May need to:
- Update package versions in requirements.txt
- Add retry logic to pip install step

## Workflow Artifacts

After each deployment, download artifacts for debugging:

1. Go to: **Actions** → Select the workflow run
2. Scroll down to **Artifacts** section
3. Download `deployment-config-<run-number>.zip`

Contains:
- `.azure-deployment.json` - Resource names and URLs
- `deploy_to_azure.log` - Full deployment logs (if created)

## Best Practices

### Branch Protection
Protect your main branch to prevent accidental deployments:
1. **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `main`
3. Enable:
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass

### Environment Protection
Add deployment protection rules:
1. **Settings** → **Environments** → **New environment**
2. Name: `production`
3. Protection rules:
   - ✅ Required reviewers (1-2 people)
   - ✅ Wait timer (optional 5-minute delay)

Then update workflow to use environment:
```yaml
jobs:
  deploy-infrastructure:
    environment: production  # Add this line
```

### Notifications
Get notified when deployments complete:
1. **Settings** → **Notifications**
2. Enable: **Email notifications for workflow runs**

Or use Slack/Teams integration via GitHub Apps marketplace.

## Comparison: PowerShell Script vs GitHub Actions

| Feature | Local PowerShell | GitHub Actions (Hybrid) |
|---------|------------------|-------------------------|
| **Authentication** | Your Azure CLI creds | Service principal OIDC |
| **Audit Trail** | None | Full Git history + logs |
| **Version Control** | Manual commits | Automatic tracking |
| **Consistency** | Your machine setup | Standardized runner |
| **Debugging** | Easy (live terminal) | Via logs + artifacts |
| **Speed** | Same (~15-20 min) | Same (~15-20 min) |
| **Flexibility** | Full control | Full control (same script) |
| **Cost** | Free (local) | Free (2000 min/month) |
| **Team Access** | Requires Azure access | GitHub permissions |

## Next Steps

Once configured:

1. **Test the workflow** - Run a deployment to a test subscription first
2. **Set up branch protection** - Prevent accidental deployments
3. **Add environment approvals** - Require manual approval for production
4. **Monitor costs** - GitHub Actions is free for public repos, check limits for private
5. **Document parameters** - Add comments to describe custom resource groups/regions

## Support

- **GitHub Actions logs**: Full output in Actions tab
- **Azure Portal**: Verify resources created correctly
- **Local debugging**: Always available via `.\deploy_to_azure.ps1`

The hybrid approach gives you the best of both worlds - automation with full control! 🚀
