# DT Logistics AI-Powered Demo Guide

## 🎯 Overview

This guide demonstrates the complete AI-powered logistics system with **5 active Azure AI Foundry agents** providing intelligent automation across the delivery workflow.

## 🤖 Active AI Agents

### 1. Customer Service Agent
**Status:** ✅ ACTIVE  
**Access:** Customer Service Chatbot page  
**Features:**
- Real-time parcel tracking via natural language
- Multi-format tracking support (DT, DTVIC, OV)
- Cosmos DB function calling for live data

### 2. Fraud Detection Agent
**Status:** ✅ ACTIVE  
**Access:** Report Fraud page  
**Features:**
- Multi-category threat analysis (phishing, impersonation, payment fraud)
- Educational content generation
- Automated workflow with Identity Agent

### 3. Identity Agent
**Status:** ✅ ACTIVE  
**Access:** Auto-triggered for high-risk cases  
**Features:**
- Customer identity verification
- Employment status validation
- Triggered automatically when fraud score ≥85%

### 4. Dispatcher Agent
**Status:** ✅ ACTIVE ⭐ NEW  
**Access:** Admin Manifests - AI Auto-Assign  
**Features:**
- Intelligent parcel-to-driver assignment
- Geographic clustering
- Workload balancing
- Priority-based distribution

### 5. Parcel Intake Agent
**Status:** ✅ ACTIVE ⭐ ENHANCED  
**Access:** Register Parcel page  
**Features:**
- Service type recommendations
- Address validation and corrections
- Delivery complication detection
- Data quality verification

## Quick Start

### Generate Demo Data

Run this command to create sample parcels and driver manifests:

```bash
cd utils/generators
python generate_demo_manifests.py
```

This creates:
- **20 sample parcels** with realistic Sydney addresses
- **3 driver manifests** distributed across drivers
- All data ready for immediate demonstration

### Sample Drivers

| Driver ID | Driver Name | Parcels |
|-----------|-------------|---------|
| `driver-001` | John Smith | 6 |
| `driver-002` | Maria Garcia | 6 |
| `driver-003` | David Wong | 8 |
| `driver-004` | Mandy Musk | 16 |

### Demo Workflow

#### 1. **AI-Powered Parcel Registration** ⭐ NEW
   - URL: http://127.0.0.1:5000/parcels/register
   - Enter parcel details (sender, recipient, weight, value)
   - **AI validates automatically:**
     - Service type recommendations (e.g., Express for high-value items)
     - Address completeness warnings
     - Delivery complication alerts (oversized, remote locations)
   - Watch for flash messages with AI insights

#### 2. **Customer Service AI Chatbot**
   - URL: http://127.0.0.1:5000/customer/chatbot
   - Ask questions in natural language:
     - "Where is my parcel DT1234567890?"
     - "Show me all deliveries for John Smith"
     - "What's the delivery status for tracking DTVIC123?"
   - Agent queries Cosmos DB in real-time

#### 3. **Fraud Detection & Analysis**
   - URL: http://127.0.0.1:5000/fraud/report
   - Paste suspicious message (SMS, email, etc.)
   - Click "Check for Frauds" button
   - **AI analyzes:**
     - Threat category (phishing, impersonation, payment fraud)
     - Risk score (0-100%)
     - Educational explanations
   - High-risk cases (≥85%) trigger Identity Agent workflow

#### 4. **AI Auto-Assign Manifests** ⭐ NEW
   - URL: http://127.0.0.1:5000/admin/manifests
   - Scroll to "AI Auto-Assign (DISPATCHER_AGENT)" section
   - Set max parcels (default: 100)
   - Optional: Filter by state (VIC, NSW, QLD, etc.)
   - Click "AI Auto-Assign Parcels"
   - **AI intelligently:**
     - Analyzes parcel locations and priorities
     - Balances driver workloads
     - Creates geographic clusters
     - Assigns to available drivers
   - View created manifests below

#### 5. **View Driver Manifest**
   - URL: http://127.0.0.1:5000/driver/manifest
   - See optimized route on embedded map
   - Mark deliveries as complete
   - Track progress with real-time updates

#### 6. **Monitor AI Agent Performance**
   - URL: http://127.0.0.1:5000/admin/agents
   - View all 5 active agents with metrics:
     - Total decisions made
     - Average confidence scores
     - Response times
     - Last execution timestamps
   - See 4 additional agents available for future integration

#### 7. **AI Insights Dashboard**
   - URL: http://127.0.0.1:5000/ai/insights
   - Comprehensive agent status overview
   - Operational analytics
   - Agent capabilities reference

## 🧪 Testing AI Agents

### Test Parcel Intake Agent
```bash
python Scripts/test_parcel_intake_agent.py
```
Tests 4 scenarios:
- Standard parcel validation
- High-value parcel (service recommendations)
- Incomplete address detection
- Oversized/remote delivery complications

### Test Dispatcher Agent
```bash
python Scripts/test_dispatcher_agent.py
```
Options:
- Quick test: Verify agent connectivity
- Full test: Create sample parcels and test assignment

### Test Customer Service Agent
1. Open chatbot: http://127.0.0.1:5000/customer/chatbot
2. Try queries:
   - "Track parcel DT1234567890"
   - "Show deliveries for [recipient name]"
   - "What's the status of DTVIC123?"

### Test Fraud Detection Workflow
1. Go to: http://127.0.0.1:5000/fraud/report
2. Paste sample fraud message:
   ```
   URGENT: Your DT Logistics parcel is held. Pay $50 fee now at 
   bit.ly/fake-link or package will be destroyed. Reply with card details.
   ```
3. Click "Check for Frauds"
4. Observe:
   - High risk score (90%+)
   - Threat category identification
   - Educational content
   - Identity verification workflow triggered

## Sample Addresses

All deliveries are in Sydney CBD area:
- Macquarie Street (CBD)
- The Rocks
- Barangaroo
- George Street
- King Street
- North Sydney (across harbour)
- Pyrmont (waterfront)

### Route Optimization

**Without Azure Maps Key:**
- Uses mock optimization
- Estimates 5km and 10min per delivery
- Still shows map placeholder

**With Azure Maps Key:**
1. Add to `.env`:
   ```
   AZURE_MAPS_SUBSCRIPTION_KEY=your_key_here
   ```
2. Restart Flask app
3. Routes will optimize with real traffic data
4. Actual distances and times calculated

### Testing Delivery Completion

1. Open driver manifest view
2. Click "Complete" button next to any delivery
3. Watch progress bar update
4. Status changes to "completed" for that item
5. When all items completed, manifest status updates

### Sample Barcode Format

Generated barcodes follow pattern:
- `DT` + `YYYYMMDD` + `####`
- Example: `DT202512040001`

### Regenerating Demo Data

Running the script multiple times will:
- Create new parcels with new barcodes
- Create new manifests with unique IDs
- Keep existing data (no deletions)

To start fresh:
- Delete items from Cosmos DB containers
- Or change barcode prefix in script

## API Endpoints

### AI Agent Endpoints

#### Auto-Assign Manifests (Dispatcher Agent)
```http
POST /auto_assign_manifests
Content-Type: application/x-www-form-urlencoded

max_parcels=100&state_filter=VIC
```
Returns: JSON with created manifests and AI recommendations

#### Check Fraud (Fraud Detection Agent)
```http
POST /check_fraud
Content-Type: application/json

{
  "message": "Suspicious message text",
  "tracking_number": "DT1234567890"
}
```
Returns: Threat analysis with risk score and category

#### Customer Service Chat
```http
POST /customer/chat
Content-Type: application/json

{
  "message": "Where is my parcel?",
  "conversation_history": []
}
```
Returns: AI response with parcel data

### Driver Manifest Endpoints

#### Get Driver Manifest
```http
GET /driver/manifest
```

Returns today's active manifest for the driver.

### Mark Delivery Complete
```http
POST /driver/manifest/<manifest_id>/complete/<barcode>
```

Marks a specific delivery as completed.

### Get All Manifests (Admin)
```http
GET /admin/manifests
```

Shows all active manifests for today.

### Create Manifest (Admin)
```http
POST /admin/manifests
Form Data:
  - driver_id: string
  - driver_name: string
  - barcodes: textarea (comma or newline separated)
```

## Customization

### Change Delivery Locations

Edit `SAMPLE_ADDRESSES` in `utils/generators/generate_demo_manifests.py`:

```python
SAMPLE_ADDRESSES = [
    {
        "recipient": "Name",
        "address": "Full Address",
        "phone": "+61 2 XXXX XXXX",
        "priority": "normal|urgent",
        "notes": "Delivery instructions"
    },
    # ... more addresses
]
```

### Add More Drivers

Edit `SAMPLE_DRIVERS` in `utils/generators/generate_demo_manifests.py`:

```python
SAMPLE_DRIVERS = [
    {"id": "driver-004", "name": "New Driver"},
    # ... more drivers
]
```

### Change Depot Location

Update `.env`:
```
DEPOT_ADDRESS=Your Warehouse Address
```

## 🎬 Demo Script Suggestions

### Scenario 1: End-to-End AI-Powered Parcel Journey

1. **Register parcel with AI validation**
   - Navigate to Register Parcel page
   - Enter high-value item ($2000+) with "Standard" service
   - Watch AI recommend "Express" or "Overnight" service
   - Show address validation feedback

2. **Auto-assign to driver**
   - Go to Admin Manifests
   - Use AI Auto-Assign with 10 parcels
   - Show AI's intelligent distribution across drivers

3. **Track with AI chatbot**
   - Open Customer Service chatbot
   - Ask: "Where is parcel [tracking number]?"
   - Show real-time status from Cosmos DB

4. **Monitor agent performance**
   - Navigate to AI Agents dashboard
   - Show metrics for all 5 active agents
   - Highlight decision counts and confidence scores

### Scenario 2: Fraud Detection Workflow

1. **Report suspicious message**
   - Submit fraud message via Report Fraud page
   - AI analyzes and categorizes threat

2. **High-risk workflow activation**
   - Show risk score ≥85%
   - Identity Agent automatically triggered
   - Demonstrate multi-agent coordination

3. **View workflow on approvals page**
   - Navigate to Approvals dashboard
   - Show fraud case with identity verification status

### Scenario 3: Operational Efficiency Demo

1. **Show pending parcels at depot**
   - Navigate to All Parcels page
   - Filter by "At Depot" status

2. **AI-powered bulk assignment**
   - Use Dispatcher Agent to auto-assign 100 parcels
   - Show geographic clustering in action

3. **Driver receives optimized manifest**
   - View driver manifest with route map
   - Show delivery sequence optimization

4. **Track delivery progress**
   - Mark deliveries complete
   - Watch progress updates in real-time

## Troubleshooting

### AI Agent Issues

#### "Agent not responding" Error
- Verify `.env` contains all agent IDs:
  ```
  CUSTOMER_SERVICE_AGENT_ID=asst_xxxxx
  FRAUD_DETECTION_AGENT_ID=asst_xxxxx
  IDENTITY_AGENT_ID=asst_xxxxx
  DISPATCHER_AGENT_ID=asst_xxxxx
  PARCEL_INTAKE_AGENT_ID=asst_xxxxx
  ```
- Check Azure AI Foundry endpoint is accessible
- Verify Azure CLI authentication: `az account show`

#### AI Validation Not Showing
- Check browser console for JavaScript errors
- Verify flash messages are enabled in base template
- Ensure session storage is working

#### Dispatcher Agent Assignment Fails
- Verify drivers exist in Cosmos DB users container
- Check parcels have "At Depot" status
- Review terminal output for detailed error messages

### "Container not found" Error
Run the setup script first:
```bash
cd Scripts
python setup_manifest_container.py
```

### No Manifests Showing
- Check that Flask app is running
- Verify you're using correct driver_id
- Check today's date matches manifest_date

### Route Not Optimizing
- Add `AZURE_MAPS_SUBSCRIPTION_KEY` to `.env`
- Check Azure Maps account is active
- Verify addresses are complete and valid

### Parcels Not Found
- Run `generate_demo_manifests.py` first
- Check barcodes match exactly
- Verify parcels were created successfully

## Production Considerations

Before using in production:

### 1. **Remove Demo Data**
   - Delete test parcels from database
   - Clear sample manifests
   - Remove test fraud reports

### 2. **Configure AI Agents**
   - Review and customize agent prompts in `agents/base.py`
   - Adjust confidence thresholds for workflows
   - Configure agent-specific tools and permissions
   - Set up monitoring and logging for agent decisions

### 3. **Configure Real Data**
   - Set actual depot address
   - Add Azure Maps subscription key
   - Configure real driver IDs
   - Update company branding in `config/company.py`

### 4. **Security**
   - Add authentication to driver routes
   - Validate driver can only see their own manifests
   - Implement proper error handling
   - Secure AI agent endpoints with authentication
   - Add rate limiting for AI agent calls

### 5. **Performance**
   - Enable Cosmos DB indexing
   - Cache route optimizations
   - Implement pagination for large manifest lists
   - Monitor AI agent response times
   - Set up Azure AI Foundry monitoring

### 6. **Agent Governance**
   - Review AI responses regularly for quality
   - Implement feedback loops for agent improvement
   - Set up alerts for low confidence scores
   - Document agent decision-making processes
   - Establish human-in-the-loop for critical decisions

## 📚 Additional Resources

### Documentation Files
- `DISPATCHER_AGENT_GUIDE.md` - Detailed dispatcher integration guide
- `AGENT_COMMUNICATION_OPPORTUNITIES.md` - Multi-agent workflow ideas
- `AZURE_DEPLOYMENT.md` - Azure deployment instructions
- `USER_AUTH_GUIDE.md` - Authentication setup guide

### Test Scripts
- `Scripts/test_parcel_intake_agent.py` - Parcel validation tests
- `Scripts/test_dispatcher_agent.py` - Assignment algorithm tests
- `Scripts/Identity_Test_CosmosDB_connection.py` - Database connectivity

### Setup Scripts
- `Scripts/A01_Create_Multiple_Foundry_Agent_Persistent.py` - Create all 9 agents
- `Scripts/setup_manifest_container.py` - Initialize Cosmos DB containers
- `utils/generators/generate_demo_manifests.py` - Generate demo data

## 🎯 Key Demo Highlights

**What makes this special:**
1. ✅ **5 Active AI Agents** working together in production
2. 🤖 **Multi-Agent Workflows** (Fraud → Identity verification)
3. 💡 **Intelligent Recommendations** (Service types, route optimization)
4. 📊 **Real-time Monitoring** (Agent performance dashboard)
5. 🔄 **Seamless Integration** (Cosmos DB, Azure Maps, Azure AI Foundry)

**Technical Stack:**
- **Azure AI Foundry** - Persistent agents with function calling
- **Cosmos DB** - NoSQL database with async Python SDK
- **Azure Maps** - Route optimization and geocoding
- **Flask** - Python web framework
- **Bootstrap 5** - Responsive UI

## Support Files

- `Scripts/setup_manifest_container.py` - Create Cosmos DB container
- `utils/generators/generate_demo_manifests.py` - Generate demo data
- `agents/base.py` - Universal agent integration layer
- `agents/fraud.py` - Fraud detection implementation
- `parcel_tracking_db.py` - Async database operations
