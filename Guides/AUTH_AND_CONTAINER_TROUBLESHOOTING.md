# Authentication & Container Troubleshooting Guide

Quick reference for resolving common Cosmos DB issues in Azure App Service deployment.

## Common Errors

### 1. Unauthorized Error ❌ (CRITICAL)

**Error Message:**
```
The input authorization token can't serve the request. 
The wrong key is being used or the expected payload is not built as per the protocol.
Code: Unauthorized
```

**Root Cause:**
- Managed identity token is stale/cached
- RBAC permissions not fully propagated (2-5 min delay)
- App started before RBAC assignment completed
- Environment variables still have key-based auth (COSMOS_DB_KEY/COSMOS_CONNECTION_STRING)

**Quick Fix (Standard):**
```powershell
# Diagnose
.\Scripts\diagnose_cosmos_auth.ps1

# Fix (assigns RBAC if missing, restarts app with fresh tokens)
.\Scripts\fix_cosmos_auth.ps1
```

**Aggressive Fix (If Standard Doesn't Work):**
```powershell
# Does a complete reset:
# - Removes ALL key-based auth environment variables
# - Completely STOPS then STARTS the app (not just restart)
# - Waits 90 seconds for RBAC propagation
.\Scripts\force_fix_auth.ps1

# This is more thorough than a regular restart and clears all cached credentials
```

---

### 2. Resource Not Found Error ❌

**Error Message:**
```
Resource Not Found. Learn more: https://aka.ms/cosmosdb-tsg-not-found
Code: NotFound
```

**Root Cause:**
- Cosmos DB containers don't exist
- Container validation step failed during deployment
- Database was deleted/recreated

**Quick Fix:**
```powershell
# Diagnose which containers are missing
python Scripts/diagnose_containers.py

# Create missing containers
.\Scripts\fix_azure_containers.ps1

# Restart app
az webapp restart --name <webapp-name> --resource-group RG-Zava-Frontend-dev
```

---

## Diagnostic Scripts

### Check Authentication
```powershell
.\Scripts\diagnose_cosmos_auth.ps1

# Checks:
# ✓ Managed identity enabled
# ✓ RBAC role assigned
# ✓ Environment variables configured
# ✓ Local auth disabled (security)
# ✓ Web app running state
```

### Check Containers
```powershell
python Scripts/diagnose_containers.py

# Checks all 10 required containers:
# - parcels (partition: /store_location)
# - TrackingEvents (partition: /barcode)
# - DeliveryAttempts (partition: /barcode)
# - feedback (partition: /tracking_number)
# - company_info (partition: /info_type)
# - suspicious_messages (partition: /report_date)
# - address_history (partition: /address_normalized)
# - users (partition: /username)
# - Manifests (partition: /manifest_id)
# - address_notes (partition: /address_normalized)
```

---

## Fix Scripts

### Fix Authentication Issues (Standard)
```powershell
.\Scripts\fix_cosmos_auth.ps1

# Actions:
# 1. Verifies managed identity is enabled
# 2. Checks/assigns RBAC permissions
# 3. Disables local auth (security)
# 4. Restarts app with fresh tokens
# 5. Waits for RBAC propagation (60 sec)
```

### Fix Authentication Issues (Aggressive)
```powershell
.\Scripts\force_fix_auth.ps1

# When standard fix doesn't work, this does a complete reset:
# 1. Removes ALL key-based auth environment variables
# 2. Verifies/assigns RBAC permissions
# 3. STOPS the app completely (not just restart)
# 4. Waits 90 seconds for RBAC propagation
# 5. STARTS the app with completely fresh credentials
# 6. Waits 45 seconds for app initialization

# This clears all cached tokens - use when standard fix fails
```
# 3. Disables local auth (security)
# 4. Restarts app with fresh tokens
# 5. Waits for RBAC propagation (60 sec)
```

### Fix Missing Containers
```powershell
.\Scripts\fix_azure_containers.ps1

# Actions:
# 1. Temporarily enables local auth
# 2. Creates all 10 containers
# 3. Re-disables local auth (security)
# 4. Provides next steps
```

---

## Manual Verification

### Check Managed Identity
```powershell
# Get principal ID
az webapp identity show `
  --name <webapp-name> `
  --resource-group RG-Zava-Frontend-dev `
  --query "principalId" -o tsv
```

### Check RBAC Assignment
```powershell
# List role assignments
az cosmosdb sql role assignment list `
  --account-name <cosmos-name> `
  --resource-group RG-Zava-Backend-dev

# Expected role: Cosmos DB Built-in Data Contributor
# Role ID: 00000000-0000-0000-0000-000000000002
```

### Check Environment Variables
```powershell
# List app settings
az webapp config appsettings list `
  --name <webapp-name> `
  --resource-group RG-Zava-Frontend-dev

# Required settings:
# - COSMOS_DB_ENDPOINT
# - COSMOS_DB_DATABASE_NAME (usually "logisticstracking")
# - USE_MANAGED_IDENTITY=true

# Should NOT have (would override managed identity):
# - COSMOS_DB_KEY
# - COSMOS_CONNECTION_STRING
```

### Restart Web App
```powershell
# Standard restart (usually sufficient)
az webapp restart `
  --name <webapp-name> `
  --resource-group RG-Zava-Frontend-dev

# Wait 30 seconds for app to reinitialize
Start-Sleep -Seconds 30
```

### Aggressive Restart (When Standard Fails)
```powershell
# Stop completely
az webapp stop --name <webapp-name> --resource-group RG-Zava-Frontend-dev

# Wait for RBAC propagation
Start-Sleep -Seconds 90

# Start fresh
az webapp start --name <webapp-name> --resource-group RG-Zava-Frontend-dev

# Wait for initialization
Start-Sleep -Seconds 45
```

**Why the difference?**
- `az webapp restart`: Quick restart, but may preserve some cached state
- `az webapp stop` then `start`: Complete teardown and rebuild, clears all caches
- Use aggressive restart when standard restart doesn't resolve auth errors

---

## Deployment Best Practices

### Post-Deployment Checklist
1. ✅ Verify containers exist: `python Scripts/diagnose_containers.py`
2. ✅ Verify auth configured: `.\Scripts\diagnose_cosmos_auth.ps1`
3. ✅ Test web app: `https://<webapp-name>.azurewebsites.net/login`
4. ✅ Check logs if failures: `az webapp log tail --name <webapp-name> --resource-group RG-Zava-Frontend-dev`

### RBAC Propagation Timeline
- **Immediate (0-30 sec):** Role assignment created in Azure AD
- **Local region (30-60 sec):** Permission available in deployment region
- **All regions (60-300 sec):** Full global propagation (can take up to 5 min)
- **App Service (requires restart):** Cached token needs refresh to pick up new permissions

### Why App Restart is Critical
App Service caches the managed identity token at startup. If RBAC is assigned after the app starts, the cached token lacks the necessary permissions. Restarting forces the app to request a fresh token with proper Cosmos DB access.

---

## Common Scenarios

### Scenario 1: Fresh Deployment
**Timeline:**
```
0:00  Deploy infrastructure (Bicep)
0:30  Assign RBAC permissions
1:00  Wait 60 sec (RBAC propagation)
1:30  Restart app (fresh tokens) ← CRITICAL
2:00  Test endpoint (should work)
```

### Scenario 2: RBAC Was Just Added
**Problem:** Added RBAC manually but app still shows "Unauthorized"

**Solution:**
```powershell
# Wait for propagation (2-3 minutes)
Start-Sleep -Seconds 120

# Restart app to get fresh tokens
az webapp restart --name <webapp-name> --resource-group RG-Zava-Frontend-dev

# Wait for app to come online
Start-Sleep -Seconds 30

# Test
curl https://<webapp-name>.azurewebsites.net/parcels
```

### Scenario 3: Containers Missing After Deployment
**Problem:** Deployment succeeded but parcel registration fails with "Resource Not Found"

**Solution:**
```powershell
# Create containers
.\Scripts\fix_azure_containers.ps1

# No restart needed (containers are infrastructure, not app config)

# Test
curl https://<webapp-name>.azurewebsites.net/parcels/register
```

---

## Logs and Debugging

### View Live Logs
```powershell
az webapp log tail `
  --name <webapp-name> `
  --resource-group RG-Zava-Frontend-dev
```

### Look for These Messages

**Good (Auth Working):**
```
Using managed identity authentication
✓ Database 'logisticstracking' exists and is accessible
✅ App startup initialization completed
```

**Bad (Auth Issues):**
```
❌ ERROR: Cannot access database
Unauthorized: The input authorization token can't serve the request
MAC signature verification failed
```

**Bad (Container Issues):**
```
Resource Not Found
Cannot find container: parcels
❌ Error registering parcel
```

---

## Support

If automated fixes don't resolve the issue:

1. **Check Azure Portal:**
   - App Service → Identity → System assigned (should be "On")
   - Cosmos DB → Settings → Keys → Local auth (should be "Disabled")

2. **Verify in Azure Portal:**
   - Cosmos DB → Access Control (IAM) → Role assignments
   - Look for your app's managed identity with "Cosmos DB Built-in Data Contributor"

3. **Contact Support:**
   - Include output from: `.\Scripts\diagnose_cosmos_auth.ps1`
   - Include app logs: `az webapp log tail ...`
   - Mention deployment timestamp and region

---

**Last Updated:** March 27, 2026  
**Version:** 1.2.5+
