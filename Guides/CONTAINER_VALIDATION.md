# Container Validation in Deployment

## Overview

The deployment script now includes **critical container validation** to ensure all required Cosmos DB containers are created and accessible before proceeding with data generation.

## What Changed

### Before (v1.2.4 and earlier)
- Container creation was attempted but not validated
- Warnings were logged if creation failed, but deployment continued
- This led to "Resource Not Found" errors when trying to register parcels
- No retry logic for RBAC propagation delays

### After (v1.2.5+)
- ✅ **Container creation is now a CRITICAL dependency**
- ✅ **Validation step** confirms all 10 containers exist
- ✅ **Automatic retry** if initial creation fails (RBAC propagation)
- ✅ **Deployment fails** if containers cannot be created/validated
- ✅ **Clear error messages** with manual fix instructions

## Deployment Flow with Dependencies

```
1. Temporarily enable Cosmos DB local auth (key-based)
   ↓
2. CREATE & VALIDATE containers (CRITICAL DEPENDENCY) ⚠️
   ├─ Creates all 10 required Cosmos DB containers
   ├─ Validates containers exist via diagnose_containers.py
   ├─ Retries once if initial creation fails (RBAC propagation delay)
   └─ DEPLOYMENT FAILS if containers cannot be created/validated
   ↓
3. Generate demo data (DEPENDS ON: containers exist)
   ├─ Fresh test parcels with DC assignments
   ├─ Dispatcher demo data (parcels at depot)
   ├─ Driver manifests with delivery parcels
   └─ Approval demo requests
   ↓
4. Re-secure Cosmos DB (disable local auth → managed identity only)
   ↓
5. Restart App Service (refresh managed identity tokens with RBAC)
```

## Required Containers (10 Total)

The deployment validates that these containers exist:

| Container | Partition Key | Purpose |
|-----------|---------------|---------|
| `parcels` | `/store_location` | Parcel records |
| `TrackingEvents` | `/barcode` | Tracking event history |
| `DeliveryAttempts` | `/barcode` | Delivery attempt records |
| `feedback` | `/tracking_number` | Customer feedback |
| `company_info` | `/info_type` | Company configuration |
| `suspicious_messages` | `/report_date` | Fraud detection logs |
| `address_history` | `/address_normalized` | Address history |
| `users` | `/username` | User accounts |
| `Manifests` | `/manifest_id` | Driver manifests |
| `address_notes` | `/address_normalized` | Delivery notes |

## Error Handling

### Scenario 1: Initial Creation Fails
**Action:** Automatic retry after 5-second wait for RBAC propagation

### Scenario 2: Validation Fails After Retry
**Action:** Deployment stops with detailed error message:

```
❌ CRITICAL ERROR: Cannot create/validate Cosmos DB containers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is a blocking issue - deployment cannot proceed without containers.

Possible causes:
  • RBAC permissions not propagated (takes 2-5 min)
  • Cosmos DB account not fully provisioned
  • Network connectivity issues

Manual fix:
  1. Wait 2-3 more minutes for RBAC propagation
  2. Run: .\Scripts\fix_azure_containers.ps1
  3. Verify: python Scripts\diagnose_containers.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Scenario 3: Manual Fix Required
If deployment fails due to container issues, use the provided scripts:

```powershell
# Diagnose which containers are missing
python Scripts/diagnose_containers.py

# Fix missing containers (works on Azure deployment)
.\Scripts\fix_azure_containers.ps1

# Optional: Specify resource group if different
.\Scripts\fix_azure_containers.ps1 -ResourceGroup "RG-Zava-Backend-dev"
```

## New Scripts Added

### 1. `Scripts/diagnose_containers.py`
**Purpose:** Check which containers exist vs. missing

**Usage:**
```bash
python Scripts/diagnose_containers.py
```

**Output:**
```
✓ parcels                    (PK: /store_location)
✓ TrackingEvents             (PK: /barcode)
✗ Manifests                  (PK: /manifest_id)        - MISSING

Status: 9/10 containers exist

💡 Run: python Scripts/initialize_all_containers.py
```

### 2. `Scripts/fix_azure_containers.ps1`
**Purpose:** Create missing containers on Azure deployment with secure auth handling

**Usage:**
```powershell
.\Scripts\fix_azure_containers.ps1
```

**What it does:**
1. Finds Cosmos DB account in resource group
2. Temporarily enables local auth (30 seconds)
3. Creates all 10 required containers
4. Immediately re-disables local auth (security)
5. Provides next steps

**Security:** Connection string is only used for container creation, then immediately removed

## Testing

### Verify Containers After Deployment

```powershell
# Check all containers exist
python Scripts/diagnose_containers.py

# Should show:
# ✅ All containers exist and are accessible!
```

### Test Parcel Registration

```powershell
# Visit the registration page
start https://zava-dev-web-77cd5n.azurewebsites.net/parcels/register

# Should work without "Resource Not Found" errors
```

## Why This Matters

### Before: Silent Failures ❌
- Containers missing → app deploys successfully
- Users visit registration page → 500 error
- Manual fix required after deployment
- Poor user experience

### After: Fail Fast ✅
- Containers missing → deployment stops immediately
- Clear error message with fix instructions
- Retry logic handles RBAC propagation delays
- Validation confirms containers exist before proceeding
- Excellent deployment reliability

## Rollback

If you need to disable strict container validation (not recommended):

```powershell
# Edit deploy_to_azure.ps1 and comment out validation:
# Line ~640-720: Comment out the validation section
```

However, this will reintroduce the "Resource Not Found" issue.

## Version History

- **v1.2.4 and earlier:** Container creation attempted, not validated
- **v1.2.5:** Added container validation as critical dependency (this change)

---

**Last Updated:** March 27, 2026  
**Deployment Script:** `deploy_to_azure.ps1`  
**Validation Scripts:** `Scripts/diagnose_containers.py`, `Scripts/fix_azure_containers.ps1`
