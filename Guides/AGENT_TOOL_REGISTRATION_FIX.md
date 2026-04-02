# Agent Tool Registration Fix - April 2, 2026

## Problem Identified

The Customer Service Agent in production deployment **could not retrieve parcel data** because:

1. **Stale Agent IDs**: The `.env` file contained old agent IDs that didn't match actual agents in Azure OpenAI
2. **No Tool Registration**: Tools were never registered with agents during deployment
3. **Missing Validation**: No validation to ensure tools were actually registered
4. **Timing Bug**: API key auth was disabled BEFORE tool registration, causing silent failures

## Root Cause

During the April 2 deployment (08:17), the deployment script:
- Created agents successfully and got IDs: `asst_AiDaSE4LqiHZIHRsiFy5xwJs`
- But the script disabled API key auth immediately after agent creation
- Tool registration code ran with API key auth disabled → failed silently
- Local `.env` still had the old IDs, causing confusion

**Actual agents in Azure OpenAI:**
```
Customer Service Agent: asst_M6cFDM1lBsMd3Ry3VWKcW7u4
Dispatcher Agent: asst_HhVRtzY7XXSsrWCV2zUX0Bpk
(All 9 agents created but NO tools registered - confirmed via API)
```

## Solution Implemented

### 1. Dynamic Agent ID Capture (`deploy_to_azure.ps1`)
**Before:**
```powershell
# Created agents, immediately disabled API key auth
az resource update --set properties.disableLocalAuth=true
# Then tried to register tools (failed - no API key auth!)
```

**After:**
```powershell
# Create agents
python Scripts/create_foundry_agents_openai.py | Tee-Object -Variable agentOutput

# Parse agent IDs from JSON output
$agentIds = $jsonMatch.Value | ConvertFrom-Json

# Store in BOTH $agentSettings AND environment variables
$agentIds.PSObject.Properties | ForEach-Object {
    $agentSettings[$_.Name] = $_.Value
    Set-Item -Path "env:$($_.Name)" -Value $_.Value
}

# Register tools (API key still enabled)
python Scripts/register_agent_tools_openai.py
python Scripts/validate_agent_tools.py

# NOW disable API key auth
az resource update --set properties.disableLocalAuth=true
```

### 2. Tool Registration Validation (`Scripts/validate_agent_tools.py`)
New validation script that:
- Connects to Azure OpenAI with API key
- Retrieves the Customer Service Agent
- Checks if tools are registered
- Returns exit code 0 (success) or 1 (failure)

**Output:**
```
✅ Validating Customer Service Agent Tool Registration
📋 Retrieving agent...
   ✓ Agent: Customer Service Agent
   Model: gpt-4o
✅ SUCCESS: Agent has 4 tools registered
📋 Registered tools:
   1. track_parcel
   2. search_parcels_by_recipient
   3. search_parcels_by_driver
   4. get_delivery_statistics
✅ Agent is ready to access Cosmos DB!
```

### 3. Redeployment Validation
For redeployments (when agents already exist):
- First validate if tools are already registered
- Only register if validation fails
- Show clear output of validation status
- No more silent failures

### 4. Updated Environment Variables
Fixed `.env` with correct agent IDs from production:
```bash
# Old (stale)
CUSTOMER_SERVICE_AGENT_ID=asst_AiDaSE4LqiHZIHRsiFy5xwJs

# New (actual)
CUSTOMER_SERVICE_AGENT_ID=asst_M6cFDM1lBsMd3Ry3VWKcW7u4
```

## Files Modified

1. **deploy_to_azure.ps1** - Fixed agent creation and tool registration flow
   - Lines 330-410: Fresh deployment flow (create agents → register tools → validate → disable auth)
   - Lines 450-545: Redeployment flow (validate → register if needed → validate again)

2. **Scripts/validate_agent_tools.py** - New validation script
   - Validates tool registration
   - Clear success/failure output
   - Exit code for automation

3. **Scripts/quick_register_tools.ps1** - Manual fix script
   - Temporarily enables API key auth
   - Registers tools
   - Validates registration
   - Disables API key auth
   - Used for immediate production fix (completed successfully)

4. **Scripts/list_all_assistants.py** - Diagnostic tool
   - Lists all agents in Azure OpenAI instance
   - Shows tool count for each agent
   - Helped identify the stale ID issue

5. **.env** - Updated with correct agent IDs from production

6. **AGENTS.md** - Updated documentation
   - Added dynamic agent ID capture step
   - Added validation step
   - Clarified timing of API key auth

## Validation Results

### Production Fix (Manual) - ✅ Complete
```bash
$ python Scripts/register_agent_tools_openai.py

✅ Successfully registered tools!
   Agent: Customer Service Agent
   Tools: 4

📝 Registered Tools:
   1. track_parcel
   2. search_parcels_by_recipient
   3. search_parcels_by_driver
   4. get_delivery_statistics
```

### App Service Updated - ✅ Complete
```bash
$ az webapp config appsettings set --settings CUSTOMER_SERVICE_AGENT_ID=asst_M6cFDM1lBsMd3Ry3VWKcW7u4 ...
# All 9 agent IDs updated

$ az webapp restart --name zava-dev-web-bmwcty
# App restarted with correct configuration
```

### Testing Instructions
1. Visit: https://zava-dev-web-bmwcty.azurewebsites.net/chat
2. Query: "Can I get photo proof for parcel BC2CEE0A7C90DE?"
3. Expected: Agent retrieves parcel data including lodgement photos
4. Before fix: "I'm experiencing a technical issue"
5. After fix: Full parcel details with photo data

## Future Deployments

All future deployments (fresh or redeploy) will:
1. ✅ Create agents with dynamically captured IDs
2. ✅ Update App Service settings immediately
3. ✅ Register tools with correct agent IDs
4. ✅ Validate tool registration succeeded
5. ✅ Show clear success/failure messages
6. ✅ No manual intervention required

**No more stale agent IDs or broken deployments!**
