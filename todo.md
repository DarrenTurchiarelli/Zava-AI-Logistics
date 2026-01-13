.# TODO List

## High Priority

### Fix Driver Location Filtering

**Status:** Temporarily Disabled  
**Issue:** Location-based filtering removed all parcels because `destination_city` values don't match driver locations  
**Location:** `app.py` lines 2033-2054

**Steps to fix:**

1. Delete all existing parcels and manifests:

   ```powershell
   cd c:\Workbench\dt_item_scanner
   py Scripts\delete_all_demo_data.py
   ```

2. Regenerate demo data with fixed city extraction:

   ```powershell
   cd utils\generators
   py generate_demo_manifests.py
   ```

3. Re-enable the location filter in `app.py`:
   - Remove the comment block wrapping the filter code (lines 2036-2054)
   - The filter ensures drivers only see parcels for their assigned city

**Why this matters:**

- Improves driver efficiency by showing only relevant deliveries
- Reduces confusion from seeing parcels outside their delivery area
- Matches real-world logistics operations

**Current workaround:** Filter is commented out, all drivers see all parcels in their manifest

---

## CI/CD & Deployment

### Enable GitHub Actions Azure Deployment

**Priority:** Medium  
**File:** `.github/workflows/deploy-azure.yml` created

**Required Setup:**

1. **Add GitHub Secrets** (Settings → Secrets and variables → Actions):

   ```bash
   # Azure Authentication (OIDC)
   AZURE_CLIENT_ID
   AZURE_TENANT_ID
   AZURE_SUBSCRIPTION_ID

   # Azure Resources
   AZURE_WEBAPP_NAME
   AZURE_RESOURCE_GROUP
   AZURE_AI_PROJECT_ENDPOINT
   AZURE_AI_PROJECT_CONNECTION_STRING
   AZURE_AI_MODEL_DEPLOYMENT_NAME
   COSMOS_DB_ENDPOINT
   COSMOS_DB_DATABASE_NAME

   # All 8 Agent IDs
   CUSTOMER_SERVICE_AGENT_ID
   FRAUD_RISK_AGENT_ID
   IDENTITY_AGENT_ID
   DISPATCHER_AGENT_ID
   PARCEL_INTAKE_AGENT_ID
   SORTING_FACILITY_AGENT_ID
   DELIVERY_COORDINATION_AGENT_ID
   OPTIMIZATION_AGENT_ID
   ```

2. **Configure Azure OIDC** (one-time setup):

   ```bash
   # Create service principal for GitHub Actions
   az ad sp create-for-rbac --name "github-actions-zava" \
     --role contributor \
     --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
     --sdk-auth

   # Copy the output JSON values to GitHub secrets
   ```

3. **Enable Workflow:**
   - Push to `main` branch triggers automatic deployment
   - Or use "Actions" tab → "Deploy to Azure" → "Run workflow"

**Benefits:**

- ✅ Automatic agent instruction updates post-deployment
- ✅ Multi-stage validation (validate → test → deploy → update agents → health check)
- ✅ Rollback capability on failure
- ✅ No hardcoded credentials (uses OIDC + Managed Identity)
- ✅ Environment-specific deployments (staging/production)

---

## Future Enhancements

### Route Optimization

- Verify all three route types (fastest, shortest, safest) use accurate Azure Maps data
- Test "Recalculate Routes" button with real manifest data

### Demo Data Generation

- Consider adding more realistic address variations
- Add edge cases (PO boxes, apartment buildings, rural addresses)
