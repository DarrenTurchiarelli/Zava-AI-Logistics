# DISPATCHER_AGENT Integration Guide

## Overview

The **DISPATCHER_AGENT** is now integrated into the DT Logistics system to provide intelligent, AI-powered parcel assignment to drivers. This agent makes autonomous decisions about which driver should receive which parcels based on multiple factors.

## What the DISPATCHER_AGENT Does

### Intelligent Decision Making
The agent analyzes and optimizes:
- **Driver Workload**: Balances parcels across available drivers
- **Geographic Clustering**: Groups nearby deliveries together
- **Priority Handling**: Ensures urgent parcels are prioritized
- **Capacity Management**: Respects driver capacity limits (max 20 parcels)
- **Service Levels**: Considers express, standard, and economy services

### What It Does NOT Do
❌ **Does NOT auto-generate Azure Maps routes** - Route optimization is driver-initiated only to avoid performance issues

## How to Use

### Option 1: Web Interface (Admin)

1. **Login** as admin user
2. Navigate to **"Manage Manifests"** page
3. Use the new **"AI Auto-Assign"** section:
   - Set max parcels to assign (default: 100)
   - Optional: Filter by state (VIC, NSW, etc.)
   - Click **"AI Auto-Assign Parcels"** button

4. The system will:
   - Get all pending parcels from depot
   - Get all available drivers
   - Call DISPATCHER_AGENT for intelligent assignment
   - Create manifests based on AI recommendations
   - Display results

### Option 2: Test Script

Run the test script to see the agent in action:

```powershell
# Quick test (verify agent works)
python Scripts/test_dispatcher_agent.py

# Then select: 1 (Quick test)
```

Or for full demonstration:
```powershell
python Scripts/test_dispatcher_agent.py

# Then select: 2 (Full test)
```

The full test will:
1. Create 25 sample parcels at depot
2. Get available drivers from database
3. Call DISPATCHER_AGENT for assignment recommendations
4. Show AI response and recommendations
5. Optionally create actual manifests

## Technical Details

### New Endpoints

**`POST /auto_assign_manifests`**
- Uses DISPATCHER_AGENT for intelligent assignment
- Parameters:
  - `max_parcels`: Maximum parcels to assign (1-500)
  - `state_filter`: Optional state filter (VIC, NSW, etc.)
- Returns: Redirects to admin manifests with success/error message

### New Database Methods

**`get_available_drivers(state: str = None)`**
- Returns list of drivers from users database
- Filters by state if provided
- Returns: List[Dict] with driver_id, name, location, capacity

**`get_pending_parcels(status: str = "At Depot", max_count: int = None)`**
- Returns parcels ready for assignment
- Default status: "At Depot"
- Returns: List[Dict] of parcel data

### Agent Integration

The DISPATCHER_AGENT is called via:
```python
from agents.base import dispatcher_agent

result = await dispatcher_agent(route_request)
```

**Input Format:**
```python
route_request = {
    "parcel_count": 25,
    "available_drivers": ["driver001", "driver002", "driver003"],
    "service_level": "standard",
    "delivery_window": "08:00 - 18:00",
    "zone": "VIC",
    "parcels": [
        {
            "barcode": "DT001",
            "address": "123 Main St, Melbourne VIC 3000",
            "postcode": "3000",
            "priority": 2  # 1=urgent, 2=standard, 3=economy
        },
        # ... more parcels
    ]
}
```

**Output Format:**
```python
{
    "success": True,
    "agent_id": "asst_xxx...",
    "response": "Based on analysis, I recommend:\n- driver001: 10 parcels...",
    "error": None  # Or error message if failed
}
```

### Fallback Behavior

If DISPATCHER_AGENT fails (auth issues, timeout, etc.), the system automatically falls back to **round-robin distribution**:
- Distributes parcels evenly across drivers
- Respects capacity limits
- Still creates manifests successfully

## Example Workflow

### Scenario: 25 Parcels, 3 Drivers

1. **System State:**
   - 25 parcels at depot (5 urgent, 15 standard, 5 economy)
   - 3 drivers available (driver001, driver002, driver003)
   - Locations: VIC postcodes 3000-3054

2. **DISPATCHER_AGENT Analysis:**
   ```
   Analyzing 25 parcels across 3 drivers in VIC zone...
   
   Recommendations:
   - driver001: 10 parcels (geographic cluster: 3000-3002, includes 2 urgent)
   - driver002: 9 parcels (geographic cluster: 3003-3050, includes 3 urgent)  
   - driver003: 6 parcels (geographic cluster: 3051-3054, economy deliveries)
   
   Workload balance: 83% average utilization
   Priority coverage: All urgent parcels assigned to experienced drivers
   ```

3. **Result:**
   - 3 manifests created
   - Intelligent distribution based on geography and priority
   - Drivers can optimize routes later (Azure Maps on-demand)

## Configuration

### Required Environment Variables

In `.env` file:
```bash
# DISPATCHER_AGENT (Required for auto-assign feature)
DISPATCHER_AGENT_ID=asst_xxxxxxxxxxxxx

# Azure AI Project (Required)
AZURE_AI_PROJECT_ENDPOINT=https://xxxxx.api.azureml.ms
AZURE_AI_CONNECTION_STRING=xxxxx
```

### Check Agent Status

Verify DISPATCHER_AGENT is configured:
```python
python Scripts/test_dispatcher_agent.py
# Select option: 1 (Quick test)
```

## Troubleshooting

### Issue: "DISPATCHER_AGENT failed"

**Possible Causes:**
1. `DISPATCHER_AGENT_ID` not set in `.env`
2. Azure authentication issues
3. Agent not created in Azure AI Foundry

**Solution:**
```powershell
# 1. Check environment variable
$env:DISPATCHER_AGENT_ID

# 2. Verify Azure login
az account show

# 3. Check agent exists in Azure AI Foundry portal
```

### Issue: "No available drivers found"

**Solution:**
```powershell
# Create default users (includes drivers)
python utils/setup/setup_users.py
```

### Issue: "No pending parcels found"

**Solution:**
```powershell
# Create sample parcels
python utils/generators/generate_sample_parcels.py

# Then update status to "At Depot"
```

## Performance Considerations

### Why No Auto-Route Optimization?

Azure Maps API calls for route optimization can take **3-10 seconds per manifest**. With multiple manifests, this becomes:
- Slow page load times
- Poor user experience
- Timeout issues

**Solution:** Route optimization is **driver-initiated only**:
1. Admin creates manifests (fast, AI-powered assignment)
2. Driver views manifest
3. Driver clicks "Optimize Route" when ready
4. Azure Maps calculates best route
5. Cached for that driver's session

This approach:
- ✅ Keeps admin interface responsive
- ✅ Allows drivers to control when optimization happens
- ✅ Prevents timeout issues with bulk operations
- ✅ Still leverages AI for intelligent assignment

## Future Enhancements

Potential improvements:
1. **Real-time workload tracking**: Track driver current load from active manifests
2. **Historical performance**: Use driver performance scores in assignment
3. **Time window constraints**: Consider customer delivery time preferences
4. **Multi-depot support**: Assign parcels across multiple depots
5. **Dynamic re-assignment**: AI suggests re-balancing if delays occur

## Summary

The DISPATCHER_AGENT brings true **agentic AI** to manifest creation:
- 🤖 Autonomous decision-making (not just API calls)
- 🎯 Intelligent workload balancing
- 📍 Geographic optimization
- ⚡ Fast assignment (no Azure Maps blocking)
- 🔄 Fallback to simple distribution if agent unavailable

This transforms basic "dump parcels on a driver" into intelligent, AI-powered logistics optimization! 🚀
