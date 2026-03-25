# Customer Service Agent Skills

## Agent Overview

**Purpose:** Real-time customer inquiries and parcel tracking  
**Type:** Interactive customer-facing agent  
**Model:** gpt-4o  
**Environment Variable:** `CUSTOMER_SERVICE_AGENT_ID`

## Core Capabilities

### 1. Parcel Tracking
- Real-time tracking by tracking number
- Status updates and location information
- Delivery timeline estimates
- Historical tracking events

### 2. Recipient Search
- Search by recipient name
- Search by postcode
- Search by delivery address
- Multiple parcel results handling

### 3. Driver Assignment Lookup
- Find parcels assigned to specific drivers
- Driver workload visibility
- Route information

### 4. Photo Evidence Display
- Lodgement photo acknowledgment
- Delivery proof of delivery photos
- Automatic display to customers
- Natural language photo references

## Tools & Functions

### Available Tools (Function Calling)

#### `track_parcel_tool`
**Purpose:** Retrieve real-time parcel information by tracking number

**Parameters:**
- `tracking_number` (string, required): The parcel tracking number

**Returns:**
- Full parcel details
- Current status and location
- Delivery information
- Contact details
- **Lodgement photos** (included in response)
- Delivery photos (if delivered)

**Example Usage:**
```python
{
  "tracking_number": "LP123456"
}
```

#### `search_parcels_by_recipient_tool`
**Purpose:** Search for parcels by recipient details

**Parameters:**
- `recipient_name` (string, optional): Recipient's name
- `recipient_postcode` (string, optional): Delivery postcode
- `recipient_address` (string, optional): Delivery address

**Returns:**
- List of matching parcels
- Basic parcel information for each result

**Example Usage:**
```python
{
  "recipient_name": "John Smith",
  "recipient_postcode": "2000"
}
```

#### `search_parcels_by_driver_tool`
**Purpose:** Find parcels assigned to a specific driver

**Parameters:**
- `driver_id` (string, required): Driver's username/ID

**Returns:**
- List of assigned parcels
- Delivery route information
- Current driver status

**Example Usage:**
```python
{
  "driver_id": "driver-001"
}
```

## Configuration

### Environment Variables
```bash
# Required
CUSTOMER_SERVICE_AGENT_ID=asst_XXX

# Shared (Required)
AZURE_AI_PROJECT_CONNECTION_STRING=host;sub;rg;project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### Tool Registration
Tools are registered via:
- **File:** `agent_tools.py` (Lines 1-370)
- **Registration:** `Scripts/recreate_agents.py` (automatically registers tools during agent creation)
- **Registration Method:** Azure AI Foundry function calling

## Prompt Engineering

### Base Instructions Location
- **System Prompt:** `Agent-Skills/customer-service/system-prompt.md` (single source of truth)
- **Loaded By:** `Scripts/recreate_agents.py` and `agents/base.py`

### Key Instruction Principles

1. **Photo Acknowledgment** (Critical)
   - Photos auto-display to customers
   - Agent MUST acknowledge photos naturally
   - Never say "check internal systems" when photos exist
   - Example: "I can see your lodgement photo showing..."

2. **Conversational Tone**
   - Friendly and professional
   - Use customer's name when known
   - Empathetic to delivery concerns

3. **Accuracy First**
   - Only provide information from tools
   - Never fabricate tracking details
   - Admit when information unavailable

4. **Proactive Assistance**
   - Offer related help
   - Suggest next steps
   - Flag potential delivery issues

## Usage Examples

### Example 1: Track Parcel
```python
from agents.base import customer_service_agent

result = await customer_service_agent({
    'details': 'Where is my parcel LP123456?',
    'public_mode': True
})

print(result['response'])
# "I can see your parcel LP123456 is currently out for delivery..."
```

### Example 2: Search by Recipient
```python
result = await customer_service_agent({
    'details': 'Find parcels for John Smith in Sydney 2000',
    'public_mode': True
})
```

### Example 3: Conversational Chat
```python
result = await customer_service_agent({
    'details': 'Can you help me track my package?',
    'public_mode': True
})
```

## Integration Points

### Web Application
- **Route:** `/api/chat` (POST)
- **File:** `customer_service_chatbot.py`
- **Frontend:** `templates/customer_tracking.html`
- **JavaScript:** `static/js/customer-dashboard.js`

### CLI Access
- **Command:** `python main.py` → Customer Service Menu
- **File:** `main.py` (Customer service option)

## Known Issues & Fixes

### Issue 1: Lodgement Photos Not Mentioned
**Status:** ✅ Fixed (v1.2.3)  
**Root Cause:** Photos weren't included in tool response  
**Solution:** Updated `agent_tools.py` (Lines 66-75) to include `lodgement_photos` in response  
**Impact:** Agent now naturally acknowledges photos

### Issue 2: Generic Responses
**Status:** ✅ Resolved  
**Root Cause:** Insufficient context in prompt  
**Solution:** Enhanced base instructions with specific scenarios  

## Performance Optimization

### Best Practices
1. **Use tracking number when available** - Most efficient query
2. **Cache agent responses** - Reduce API calls for repeated queries
3. **Batch recipient searches** - When multiple parcels expected
4. **Monitor RU consumption** - Track Cosmos DB usage

### Response Time Targets
- Simple tracking query: < 2 seconds
- Search queries: < 3 seconds
- Complex multi-parcel: < 5 seconds

## Testing

### Unit Tests
```bash
# Test agent connectivity
python Scripts/check_demo_parcel.py

# Test specific tracking number
python -c "import asyncio; from agents.base import customer_service_agent; asyncio.run(customer_service_agent({'details': 'Track LP123456', 'public_mode': True}))"
```

### Integration Tests
```bash
# Start Flask app
python app.py

# Test chatbot endpoint
curl -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"message": "Where is LP123456?"}'
```

## Troubleshooting

### Agent Not Responding
```bash
# Verify agent ID is set
echo $env:CUSTOMER_SERVICE_AGENT_ID

# Check Azure connection
az account show

# View agent in portal
# Visit: https://ai.azure.com → Your Project → Agents
```

### Tool Calls Failing
```bash
# Verify Cosmos DB connection
python parcel_tracking_db.py

# Check RBAC permissions
az role assignment list --assignee <principal-id>

# Recreate agents if tools were updated
python Scripts/recreate_agents.py
```

### Photos Not Displaying
```bash
# Verify lodgement_photos in parcel document
# Check database query includes photo fields
# Confirm agent instructions reference photos
```

## Version History

- **v1.2.3** (2026-01-13): Fixed lodgement photo display
- **v1.2.0** (2025-12-18): Added multi-tool support
- **v1.1.0** (2025-12): Initial customer service agent

## Related Documentation

- [AGENTS.md](../../../AGENTS.md) - Complete agent system overview
- [agent_tools.py](../../../agent_tools.py) - Tool implementations
- [agents/base.py](../../../agents/base.py) - Agent client code

## Maintenance Notes

### Updating Agent Instructions
1. Edit system prompt: `Agent-Skills/customer-service/system-prompt.md`
2. Run `python Scripts/recreate_agents.py` to update agent in Azure AI Foundry

### Adding New Tools
1. Define function in `agent_tools.py`
2. Add to `AGENT_TOOLS` list with OpenAPI schema
3. Run `python Scripts/recreate_agents.py` to register new tools
4. Update this documentation

---

**Last Updated:** March 17, 2026  
**Maintained By:** Zava Logistics Team
