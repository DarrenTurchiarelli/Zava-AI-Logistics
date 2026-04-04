# GitHub Actions Quick Reference

## Running a Deployment

### From GitHub Web UI
1. Go to **Actions** tab
2. Click **Deploy Infrastructure & Application (PowerShell)**
3. Click **Run workflow** button
4. Select options:
   - **Branch**: `main` (or your target branch)
   - **Resource Group**: Leave empty for default `RG-Zava-*`
   - **Location**: `australiaeast` (recommended)
   - **SKU**: `B2` (good balance of cost/performance)
5. Click **Run workflow**
6. ⏱️ Wait 15-20 minutes

### From GitHub CLI
```bash
# Install GitHub CLI first: https://cli.github.com/

# Run with defaults
gh workflow run deploy-infrastructure.yml

# Run with custom parameters
gh workflow run deploy-infrastructure.yml \
  -f resource_group="RG-Zava-Test" \
  -f location="eastus" \
  -f sku="B1"

# Watch the run in real-time
gh run watch

# View recent runs
gh run list --workflow=deploy-infrastructure.yml
```

## Monitoring Deployment

### Live Progress
- **Actions tab** → Click the running workflow
- Expand each step to see real-time logs
- Look for green checkmarks ✅ or red X's ❌

### Download Logs
After completion (success or failure):
1. Scroll to **Artifacts** section
2. Download `deployment-config-<run-number>.zip`
3. Extract to see `.azure-deployment.json`

## Checking Deployment Status

### Via Workflow Summary
After successful deployment, the summary shows:
- 🌐 Application URL
- 🔑 Login credentials (admin/admin123)
- 📦 Demo data confirmation
- 🤖 AI agents status
- 📋 Resource group names

### Via Azure Portal
```powershell
# List all resources in your resource groups
az resource list --resource-group RG-Zava-Frontend-dev -o table
az resource list --resource-group RG-Zava-Middleware-dev -o table
az resource list --resource-group RG-Zava-Backend-dev -o table
az resource list --resource-group RG-Zava-Shared-dev -o table
```

## Common Scenarios

### Scenario 1: First-Time Deployment
```
✅ Use: Default parameters
   Resource Group: (empty) → Auto-generates RG-Zava-*
   Location: australiaeast
   SKU: B2
   
⏱️  Duration: 15-20 minutes
📊 Resources: ~15 Azure resources created
```

### Scenario 2: Testing in Different Region
```
✅ Use: Custom location
   Resource Group: RG-Zava-Test-EastUS
   Location: eastus
   SKU: B1 (cheaper for testing)
   
💡 Tip: Use B1 SKU for dev/test to save costs
```

### Scenario 3: Production Deployment
```
✅ Use: Production SKU
   Resource Group: RG-Zava-Production
   Location: australiaeast
   SKU: P1V2 (or higher for production)
   
🔒 Recommended: Enable environment protection
   Settings → Environments → production → Required reviewers
```

### Scenario 4: Redeployment (Update Existing)
```
✅ Same parameters as original deployment
   The script auto-detects existing resources
   Updates infrastructure + redeploys code
   
⚠️  Note: Demo data will be regenerated
```

## Workflow Status Icons

| Icon | Status | Meaning |
|------|--------|---------|
| 🟡 | Queued | Waiting to start |
| 🔵 | In Progress | Currently running |
| ✅ | Success | Deployment completed |
| ❌ | Failure | Deployment failed |
| ⚪ | Cancelled | Manually stopped |

## Troubleshooting Quick Fixes

### Error: "Failed to login to Azure"
```powershell
# Verify OIDC credentials
az ad app federated-credential list --id <client-id>

# Check GitHub secrets exist
# Settings → Secrets and variables → Actions
# Ensure: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID
```

### Error: "Insufficient permissions"
```powershell
# Re-grant roles to service principal
az role assignment create \
  --assignee <client-id> \
  --role Contributor \
  --scope /subscriptions/<subscription-id>

az role assignment create \
  --assignee <client-id> \
  --role "Role Based Access Control Administrator" \
  --scope /subscriptions/<subscription-id>
```

### Error: "Container validation failed"
- **Cause**: RBAC propagation delay
- **Fix**: Re-run the workflow (will retry automatically)
- **Prevention**: None (Azure timing issue)

### Deployment Stuck at Agent Creation
- **Cause**: Azure OpenAI API throttling
- **Fix**: Wait 5 minutes, re-run workflow
- **Prevention**: Don't run multiple deployments simultaneously

## Cost Estimates

### GitHub Actions Usage
- **Public repos**: Unlimited free minutes
- **Private repos**: 2000 free minutes/month, then $0.008/min
- **This workflow**: ~20 minutes per run
- **Monthly allowance**: ~100 deployments (private repos)

### Azure Resources (Monthly)
| SKU | Estimated Cost (AUD) |
|-----|----------------------|
| B1  | ~$15/month |
| B2  | ~$30/month |
| S1  | ~$100/month |
| P1V2| ~$150/month |

Plus:
- Cosmos DB: ~$25/month (400 RU/s)
- Azure OpenAI: Pay-per-use (~$5-20/month for demos)
- Storage/Maps: <$5/month

**Total**: $45-180/month depending on SKU

## Best Practices

### ✅ DO
- Run deployments during off-peak hours
- Test in dev environment first (`eastus`, `B1` SKU)
- Download and archive deployment artifacts
- Use descriptive resource group names
- Enable branch protection for `main`
- Set up environment approvals for production

### ❌ DON'T
- Run multiple deployments to same resource group simultaneously
- Deploy to production without testing first
- Ignore failed deployments (investigate logs)
- Use the same resource group for dev and production
- Commit sensitive data to the repository

## Maintenance

### Weekly
- Check GitHub Actions usage (Settings → Billing)
- Review Azure costs (portal.azure.com → Cost Management)

### Monthly
- Rotate service principal credentials (if not using OIDC)
- Update Python dependencies (`pip list --outdated`)
- Review deployment logs for warnings

### Quarterly
- Update Bicep templates with new Azure features
- Review and optimize Cosmos DB RU/s allocation
- Check for Azure OpenAI model updates

## Support

- **Setup issues**: See [GITHUB_ACTIONS_SETUP.md](./GITHUB_ACTIONS_SETUP.md)
- **Deployment errors**: Check workflow logs + artifacts
- **Azure issues**: Review deployment script output
- **Local testing**: Always available via `.\deploy_to_azure.ps1`

---

**Remember**: The hybrid approach runs the exact same PowerShell script - just triggered from GitHub Actions instead of your local machine. All the script's features, retries, and error handling work identically! 🚀
