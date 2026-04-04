# AGENTS.md

Technical documentation for AI coding agents working with the Zava Azure AI-powered parcel tracking system.

## Project Overview

Zava is a last-mile delivery platform powered by **8 Azure AI Foundry agents** with end-to-end intelligent automation. Built with Flask, Azure Cosmos DB, Azure Maps, and the Microsoft Agent Framework.

**Tech Stack:**
- Python 3.11+
- Flask 3.0+ (web framework with Blueprint architecture)
- Azure Cosmos DB (NoSQL database with Repository pattern)
- Azure AI Foundry (persistent agents)
- Azure Maps (route optimization)
- Azure Speech Services (voice features)
- Azure Vision (OCR/image analysis)

**Architecture:**
- **Clean Architecture** - 5 distinct layers (interfaces, application, domain, infrastructure, config)
- **Domain-Driven Design** - Business logic in domain services
- **CQRS Pattern** - Separate read/write models
- **Repository Pattern (modern Python packaging)
pip install -e ".[dev]"
# Or just production dependencies
pip install -e .

# Legacy requirements.txt also supported
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Then edit with your Azure credentials

# Initialize database
python -m src.infrastructure.database.cosmos_client
# Or use the legacy script
python archive/legacy_modules/parcel_tracking_db.py

# Generate demo data
python utils/generators/generate_fresh_test_data.py
python utils/generators/generate_dispatcher_demo_data.py
python utils/generators/generate_demo_manifests.py

# Run tests
pytest tests/ -vt
# Or use the legacy script
python archive/legacy_modules/parcel_tracking_db.py

# Generate demo data
python utils/generators/generate_fresh_test_data.py
python utils/generators/generate_dispatcher_demo_data.py
python utils/generators/generate_demo_manifests.py
```

### Development
```bash
# Start web app (development)
$env:FLASK_ENV='development'; py app.py

# Start with debug mode
$env:DEBUG_MODE='true'; py app.py

# Start CLI interface
python main.py
```

### Production
```bash
# Start web app (production)
py app.py

# Deploy to Azure (automatically registers resource providers)
.\deploy_to_azure.ps1

# Redeploy to existing instance
.\deploy_to_azure.ps1  # Automatically detects .azure-deployment.json
```

**Deployment Features:**
- ✅ Automatic resource provider registration (works on fresh subscriptions)
- ✅ Complete infrastructure via Bicep (Cosmos DB, AI Hub, Maps, etc.)
- ✅ RBAC permissions configured automatically
- ✅ Demo data and users initialized
- ✅ **Agents created AND tools registered automatically**
- ✅ **Agent IDs dynamically captured and validated**
- ✅ **Tool registration validated before deployment completes**
- ✅ No manual Azure portal configuration needed

## Azure AI Foundry Agents

### Quick Reference

| Agent | Env Var | File | Tools | Status |
|-------|---------|------|-------|--------|
| Customer Service | `CUSTOMER_SERVICE_AGENT_ID` | src/infrastructure/agents/core/base.py | track_parcel, search_parcels | ✅ Active |
| Fraud Detection | `FRAUD_RISK_AGENT_ID` | src/infrastructure/agents/core/fraud.py | None | ✅ Active |
| Identity Verification | `IDENTITY_AGENT_ID` | src/infrastructure/agents/core/base.py | None | ✅ Active |
| Dispatcher | `DISPATCHER_AGENT_ID` | src/infrastructure/agents/core/manifest.py | None | ✅ Active |
| Parcel Intake | `PARCEL_INTAKE_AGENT_ID` | src/infrastructure/agents/core/base.py | None | ✅ Active |
| Sorting Facility | `SORTING_FACILITY_AGENT_ID` | src/infrastructure/agents/core/base.py | None | ✅ Active |
| Delivery Coordination | `DELIVERY_COORDINATION_AGENT_ID` | src/infrastructure/agents/core/base.py | None | ✅ Active |
| Optimization | `OPTIMIZATION_AGENT_ID` | src/infrastructure/agents/core/base.py | None | ✅ Active |

### 1. Customer Service Agent 🎧
**Purpose:** Real-time customer inquiries and parcel tracking

**Environment Variables:**
- `CUSTOMER_SERVICE_AGENT_ID` - Azure AI Foundry agent ID (asst_XXX)

**Tools:** (Cosmos DB function calling)
- `track_parcel_tool` - Real-time parcel tracking by tracking number
- `search_parcels_by_recipient_tool` - Search by name/postcode/address
- `search_parcels_by_driver_tool` - Search by driver assignment

**Tool Registration:**
- ✅ **Automatically registered during deployment**
- Tools enable agent to query Cosmos DB in real-time
- No manual configuration needed

**Prompt Locations:**
- Base instructions: Azure AI Foundry portal or scripts/register_agent_tools_openai.py
- Runtime implementation: src/infrastructure/agents/core/base.py
- System prompts: src/infrastructure/agents/skills/customer-service/system-prompt.md
- ⚠️ **IMPORTANT**: Photos (lodgement_photos/delivery_photos) auto-display to customers. Agent must acknowledge them naturally, never say "check internal systems" when photos exist.

**Code Example:**
```python
from src.infrastructure.agents import customer_service_agent

result = await customer_service_agent({
    'details': 'Where is my parcel LP123456?',
    'public_mode': True  # For conversational chat
})
```

**Known Issues:**
- ✅ Fixed v1.2.3: Lodgement photos now included in agent tool response (src/infrastructure/agents/tools/cosmos_tools.py)

### 2. Fraud Detection Agent 🛡️
**Purpose:** Security threat analysis and scam detection

**Environment Variables:**
- `FRAUD_RISK_AGENT_ID` - Azure AI Foundry agent ID

**Features:**
- Multi-category threat analysis (phishing, impersonation, payment fraud)
- Risk score calculation (0-100%)
- Automatic workflow triggering at ≥70% risk score

**Code Example:**
```python
from src.infrastructure.agents import fraud_risk_agent
# Or use the domain service for business logic
from src.domain.services import FraudService

result = await fraud_risk_agent({
    'message_content': 'Suspicious SMS text',
    'sender_email': 'unknown@example.com',
    'activity_type': 'message'
})
```

**Workflow Integration:**
- High risk (≥70%): Triggers customer notification via Customer Service Agent
- Very high risk (≥85%): Triggers Identity Verification Agent
- Critical (≥90%): Automatic parcel hold

### 3. Identity Verification Agent 🔐
**Purpose:** Customer identity verification for high-risk cases

**Environment Variables:**
- `IDENTITY_AGENT_ID` - Azure AI Foundry agent ID

**Auto-Triggered:** When fraud risk ≥85%

**Code Example:**
```python
from src.infrastructure.agents import identity_agent

result = await identity_agent({
    'customer_name': 'John Smith',
    'verification_request': 'Verify employment status',
    'verification_reason': 'High-risk fraud detection'
})
```

### 4. Dispatcher Agent 📋
**Purpose:** Intelligent parcel-to-driver assignment

**Environment Variables:**
- `DISPATCHER_AGENT_ID` - Azure AI Foundry agent ID

**Features:**
- Geographic clustering
- Workload balancing
- Priority-based distribution
- Capacity optimization

**Access:** Admin Manifests → AI Auto-Assign

### 5. Parcel Intake Agent 📦
**Purpose:** New parcel validation and recommendations

**Environment Variables:**
- `PARCEL_INTAKE_AGENT_ID` - Azure AI Foundry agent ID

**Features:**
- Service type recommendations
- Address validation
- Delivery complication predictions
- Weight/dimension verification

**Code Example:**
```python
from src.infrastructure.agents import parcel_intake_agent
# Or use the domain service for validation
from src.domain.services import ParcelService

result = await parcel_intake_agent({
    'tracking_number': 'DT123456',
    'sender_name': 'John Smith',
    'recipient_address': '123 Main St, Sydney NSW 2000',
    'weight_kg': 1.5,
    'service_type': 'express'
})
```

### 6. Sorting Facility Agent 🏭
**Purpose:** Facility capacity monitoring and routing decisions

**Environment Variables:**
- `SORTING_FACILITY_AGENT_ID` - Azure AI Foundry agent ID

**Features:**
- Real-time capacity monitoring
- Automated routing decisions
- Load balancing
- Priority-based routing

### 7. Delivery Coordination Agent 🚚
**Purpose:** Multi-stop delivery sequencing and customer notifications

**Environment Variables:**
- `DELIVERY_COORDINATION_AGENT_ID` - Azure AI Foundry agent ID

**Features:**
- Delivery route sequencing
- Automated SMS/email notifications
- Dynamic route adjustments
- Time window management

### 8. Optimization Agent 📊
**Purpose:** Network-wide performance analysis and cost reduction

**Environment Variables:**
- `OPTIMIZATION_AGENT_ID` - Azure AI Foundry agent ID

**Features:**
- Cost reduction insights
- Resource allocation optimization
- Predictive analytics
- Performance recommendations

## Environment Variables

### Required Core Variables
```bash
# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com
AZURE_AI_PROJECT_CONNECTION_STRING=<connection-string>
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o

# Azure Cosmos DB
COSMOS_DB_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_DB_DATABASE_NAME=logisticstracking

# For local development (use connection string)
COSMOS_CONNECTION_STRING=AccountEndpoint=...;AccountKey=...

# For Azure deployment (use managed identity)
USE_MANAGED_IDENTITY=true

# Flask
FLASK_SECRET_KEY=<random-32-char-string>
FLASK_ENV=production
PORT=5000
```

### Agent IDs (All Required)
```bash
CUSTOMER_SERVICE_AGENT_ID=asst_XXX
FRAUD_RISK_AGENT_ID=asst_XXX
IDENTITY_AGENT_ID=asst_XXX
DISPATCHER_AGENT_ID=asst_XXX
PARCEL_INTAKE_AGENT_ID=asst_XXX
SORTING_FACILITY_AGENT_ID=asst_XXX
DELIVERY_COORDINATION_AGENT_ID=asst_XXX
OPTIMIZATION_AGENT_ID=asst_XXX
```

### Optional Services
```bash
# Azure Maps (route optimization)
AZURE_MAPS_SUBSCRIPTION_KEY=your-key

# Azure Speech (voice features)
AZURE_SPEECH_KEY=your-key
AZURE_SPEECH_REGION=australiaeast

# Azure Vision (OCR/image analysis)
AZURE_VISION_ENDPOINT=https://your-account.cognitiveservices.azure.com
AZURE_VISION_KEY=your-key
```

## Demo Data Generation

### Approval Agent Mode Demo Parcels

Generate specialized parcels to demonstrate the AI-powered approval/denial system:

```bash
# Navigate to generators directory
cd utils/generators

# Run the generator
python generate_sample_parcels.py

# Select option 3: Generate APPROVAL DEMO parcels
```

**What it creates:**
- ✅ **3 Auto-Approve parcels** - Low risk, verified, or delivered parcels
- ❌ **4 Auto-Deny parcels** - High fraud risk, blacklisted, duplicate, or missing docs
- ⚠️ **4 Manual Review parcels** - Medium risk, high value, or complex situations

**Demo Instructions:**
1. Login as `depot_mgr` (password: `depot123`)
2. Navigate to Approvals page
3. Enable Agent Mode with recommended settings:
   - Low risk threshold: 10%
   - High risk threshold: 70%
   - Value threshold: $100
   - Enable all checkboxes
4. Click "Process with AI Agent"
5. Observe automated decisions with explanations

**Detailed Guide:** See [docs/APPROVAL_DEMO_GUIDE.md](docs/APPROVAL_DEMO_GUIDE.md) for complete walkthrough
**Quick Reference:** See [docs/APPROVAL_DEMO_QUICK_REFERENCE.md](docs/APPROVAL_DEMO_QUICK_REFERENCE.md) for demo script

**Key Demo Points:**
- Speed: Processes 11 requests in seconds
- Consistency: Same criteria every time
- Focus: Frees managers for complex cases
- Audit: Every decision logged with AI reasoning
- Flexibility: Adjustable thresholds for risk tolerance

### Bulk Realistic Data (Production-Scale Testing)

Generate thousands of realistic parcels for comprehensive testing and demos:

```bash
# Generate 2,000 realistic parcels (default)
python utils/generators/generate_bulk_realistic_data.py

# Generate custom amount
python utils/generators/generate_bulk_realistic_data.py --count 5000
```

**What it creates:**
- 🎤 **Specific demo parcels** for Voice & Text Examples (ALWAYS CREATED):
  - `RG857954` - Dr. Emma Wilson (Sydney NSW) - Out For Delivery
  - `DT202512170037` - Sarah Johnson (Perth WA) - Delivered with photo proof
  - Full event histories, photos, sender data
  - **NOTE**: These 2 parcels are also auto-created during deployment (with 100 additional realistic parcels)

- 📦 **Thousands of realistic parcels** distributed across:
  - All 8 Australian states (NSW, VIC, QLD, WA, SA, TAS, ACT, NT)
  - Proportional to population (32% NSW, 26% VIC, 20% QLD, etc.)
  - Major cities (Sydney, Melbourne, Brisbane, Perth, Adelaide, etc.)

- 📊 **Complete data for testing:**
  - Driver manifests (57 drivers with assigned parcels)
  - Approval system (parcels at various risk levels)
  - Event histories (tracking timeline)
  - Photo proofs (lodgement and delivery photos)
  - Statistics queries (parcels by state, status, etc.)

**Voice & Text Examples (Ready to Test):**
```
"Track parcel RG857954"
"Photo proof for parcel DT202512170037"
"Show me the full history for RG857954"
"Who sent parcel RG857954?"
"Find parcels for Dr. Emma Wilson"
"Show me delivery statistics for Western Australia"
```

**Automated Deployment:**
The deployment script (`deploy_to_azure.ps1`) will prompt you to generate bulk data after deployment completes. Just answer 'y' and specify the count (default: 2000 parcels).

**Generation Time:**
- 1,000 parcels: ~3-5 minutes
- 2,000 parcels: ~5-10 minutes
- 5,000 parcels: ~15-20 minutes

**Distribution Weights:**
- NSW: 32% (most populous state)
- VIC: 26%
- QLD: 20%
- WA: 11%
- SA: 7%
- TAS: 2%
- ACT: 2%
- NT: 1%

## Testing

### Run Application Tests
```bash
# Run modern test suite
pytest tests/ -v

# Test database connection (legacy)
python archive/legacy_modules/parcel_tracking_db.py

# Test database connection (new)
python -m src.infrastructure.database.cosmos_client

# Test Azure Maps integration
python -m src.infrastructure.external_services.azure_maps

# Test agent workflow
python scripts/W01_Sequential_Workflow_Human_Approval.py
```

### Manual Testing
```bash
# Test Customer Service Agent with tools
python scripts/register_agent_tools_openai.py

# Generate test parcels
python scripts/check_demo_parcel.py

# Test driver manifest generation
python utils/generators/generate_demo_manifests.py

# Run test suite
pytest tests/ -v
```

### View Logs
```bash
# Local development
# Logs print to console

# Azure App Service
az webapp log tail --name <webapp-name> --resource-group RG-Zava-Logistics

# View in portal
# https://portal.azure.com → App Service → Log stream
```

## Code Style & Conventions

### Python
- Follow PEP 8 style guide
- Use type hints for function parameters and returns
- Use async/await for database and agent operations
- Prefix internal functions with underscore: `_helper_function()`

### Agent Prompts (✨ NEW: Centralized Management)
**All agent system prompts are now managed in the `src/infrastructure/agents/skills/` folder:**

```
src/infrastructure/agents/skills/
  customer-service/
    system-prompt.md  # Base agent behavior and instructions
    SKILLS.md         # Capabilities documentation
  dispatcher/
    system-prompt.md
    SKILLS.md
  ... (other agents)
```

**Validation Status**: ✅ **All 9 agents validated** (April 3, 2026)
- Run `python scripts/validate_agent_skills.py` to re-validate
- See [AGENT_SKILLS_VALIDATION_REPORT.md](docs/AGENT_SKILLS_VALIDATION_REPORT.md) for details

**Loading Prompts in Code:**
```python
from src.infrastructure.agents.core.prompt_loader import get_agent_prompt, get_agent_skills

# Load system prompt for an agent
prompt = get_agent_prompt("customer-service")
skills = get_agent_skills("customer-service")

# List all available agents
from src.infrastructure.agents.core.prompt_loader import list_available_agents
agents = list_available_agents()
```

**Key Benefits:**
- ✅ Single source of truth for agent behavior
- ✅ No duplicated prompts across codebase
- ✅ Easy to update agent instructions without code changes
- ✅ Version control for agent prompts
- ✅ Automatic validation on import
- ✅ **Deployed to Azure AI Foundry during deployment** (via `create_foundry_agents_openai.py`)

**Deployment Integration:**
- Deployment script (`deploy_to_azure.ps1`) automatically loads prompts from skills folder
- Creates agents in Azure AI Foundry with correct instructions
- Registers tools with Customer Service Agent
- Validates tool registration succeeded
- All managed identity authentication configured

### Agent Functions
```python
async def agent_name(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Brief description of agent purpose

    Args:
        request_data: Description of expected input

    Returns:
        Dictionary with success, response, and metadata
    """
    message = f"""
    Structured prompt for agent...
    """
    return await call_azure_agent(AGENT_ID, message, request_data)
```

### Database Operations
```python
# Old way (direct database access - deprecated)
from archive.legacy_modules.parcel_tracking_db import ParcelTrackingDB
async with ParcelTrackingDB() as db:
    result = await db.operation()

# New way (repository pattern - recommended)
from src.infrastructure.database import get_cosmos_client
from src.infrastructure.database.repositories import ParcelRepository

async with await get_cosmos_client() as client:
    repository = ParcelRepository(client.database)
    parcel = await repository.get_by_tracking_number("DT123456")
```

### Naming Conventions
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case()`
- Constants: `UPPER_SNAKE_CASE`
- Agent env vars: `AGENT_NAME_AGENT_ID`

## Deployment

### Deploy to Azure App Service
```powershell
# First deployment
.\deploy_to_azure.ps1

# Redeploy (updates code only)
.\deploy_to_azure.ps1

# Force new deployment
.\deploy_to_azure.ps1 -Force

# Custom configuration
.\deploy_to_azure.ps1 -ResourceGroup "my-rg" -Location "australiaeast" -Sku "B2"
```

### Post-Deployment Steps
1. Wait 2-5 minutes for RBAC permissions to propagate (automatic in script)
2. Default users auto-created during deployment (admin, driver001-003, etc.)
3. Test login at: `https://<webapp-name>.azurewebsites.net/login` (admin/admin123)
4. Check logs if needed: `az webapp log tail --name <webapp-name> --resource-group RG-Zava-Logistics`

### Deployment Script Actions
The deployment script automatically:
1. ✅ Creates/updates Azure resources (App Service, Cosmos DB, AI Hub, **Azure OpenAI**, etc.)
2. ✅ Deploys GPT-4o model to Azure OpenAI (GlobalStandard SKU)
3. ✅ Enables managed identity on all services (Cosmos DB, Speech, Vision, OpenAI)
4. ✅ **Configures all RBAC permissions via Bicep template:**
   - Cosmos DB Built-in Data Contributor (data plane access)
   - Cognitive Services OpenAI User (for App Service, AI Hub, AI Project)
   - Cognitive Services User (Speech & Vision services)
   - **Waits 60 seconds for RBAC replication across Azure regions**
   - **Retries operations if permissions not immediately available**
5. ✅ **Creates all 8 Azure AI Foundry agents automatically using Azure OpenAI Assistants API** 🆕
   - Temporarily enables API key authentication for agent creation and tool registration
   - Creates all 8 agents via Assistants API
   - **Dynamically captures agent IDs from creation output** 🆕
   - **Immediately updates App Service settings with correct agent IDs** 🆕
   - **Registers Cosmos DB tools with Customer Service Agent** 🆕
   - **Validates tool registration succeeded** 🆕
   - **Immediately disables API key authentication (switches back to managed identity)**
6. ✅ Deploys application code
7. ✅ Sets all environment variables including agent IDs
8. ✅ **Initializes default user accounts** (admin, drivers, depot_mgr, support)
9. ✅ **Generates demo data automatically (with secure auth handling):**
   - Temporarily enables Cosmos DB local auth for data generation
   - Fresh test parcels with valid DC assignments
   - Parcels ready for dispatcher assignment (at depot)
   - **Driver manifests with delivery parcels (all drivers)**
   - **Immediately re-secures Cosmos DB (managed identity only)**
10. ✅ Tests endpoint connectivity

**Security Note**:
- Cosmos DB local auth is temporarily enabled **only** during demo data generation (30 seconds), then immediately disabled
- API key authentication is temporarily enabled **only** during agent creation (30 seconds), then immediately disabled
- All runtime operations use managed identity exclusively - no keys are stored in environment variables or configuration
- **All identity/RBAC management is consolidated in the Bicep template and deployment script** - no manual role assignments needed

The deployment is fully automated - no manual steps required for a working demo!

### Authentication Methods

**Local Development:**
- Uses Azure CLI credentials (`az login`)
- Requires `.env` file with connection strings

**Azure App Service:**
- Uses Managed Identity (no keys stored)
- RBAC roles automatically assigned by deployment script
- Environment variables configured in App Service settings

## Troubleshooting

### Cosmos DB Authentication Errors (Unauthorized) ⚠️ CRITICAL
**Symptom:** "The input authorization token can't serve the request" or "Unauthorized" errors when accessing parcels/data

**Root Cause:** Managed identity token is stale/cached, or RBAC permissions haven't propagated (takes 2-5 minutes after deployment)

**Solution 1 - Standard Fix (Try First):**
```powershell
# 1. Diagnose the issue
.\scripts\diagnose_cosmos_auth.ps1

# 2. Fix authentication issues
.\scripts\fix_cosmos_auth.ps1
```

**Solution 2 - Aggressive Fix (If Standard Fix Doesn't Work):**
```powershell
# This does a complete reset:
# - Removes ALL key-based auth environment variables
# - Completely stops and restarts the app
# - Waits 90 seconds for RBAC propagation
.\scripts\force_fix_auth.ps1
```

**Manual Solution (Last Resort):**
```powershell
# 1. Remove key-based auth environment variables
az webapp config appsettings delete `
  --name <webapp-name> `
  --resource-group RG-Zava-Frontend-dev `
  --setting-names COSMOS_DB_KEY COSMOS_CONNECTION_STRING

# 2. Set managed identity mode
az webapp config appsettings set `
  --name <webapp-name> `
  --resource-group RG-Zava-Frontend-dev `
  --settings USE_MANAGED_IDENTITY=true

# 3. Check RBAC role assignment
az cosmosdb sql role assignment list `
  --account-name <cosmos-name> `
  --resource-group RG-Zava-Backend-dev

# 4. STOP the app completely
az webapp stop --name <webapp-name> --resource-group RG-Zava-Frontend-dev

# 5. Wait for RBAC propagation
Start-Sleep -Seconds 90

# 6. START the app with fresh credentials
az webapp start --name <webapp-name> --resource-group RG-Zava-Frontend-dev

# 7. Wait for app to initialize
Start-Sleep -Seconds 45

# 8. Test: https://<webapp-name>.azurewebsites.net/parcels
```

**Why This Happens:**
1. App Service caches managed identity tokens when it starts
2. If RBAC permissions are assigned after app startup, the cached token lacks permissions
3. Environment variables with `COSMOS_DB_KEY` or `COSMOS_CONNECTION_STRING` override managed identity
4. Regular restart doesn't clear all cached credentials - need full stop/start
5. RBAC propagation across Azure regions can take 2-5 minutes

**Common Causes of Persistent Errors:**
- ❌ App still has `COSMOS_DB_KEY` or `COSMOS_CONNECTION_STRING` environment variables
- ❌ RBAC role not yet propagated (wait full 5 minutes)
- ❌ App was restarted but not stopped - cached credentials remain
- ❌ Multiple managed identities configured (system vs user-assigned)
- ❌ Cosmos DB local auth was re-enabled accidentally

**✅ Fixed in v1.2.5:** Deployment script now automatically restarts the app after RBAC assignment

### Cosmos DB Resource Not Found Errors
**Symptom:** "Resource Not Found" errors when trying to register parcels or access data

**Root Cause:** Required Cosmos DB containers don't exist in the database

**Solution (Automated):**
```powershell
# 1. Diagnose which containers are missing
python scripts/diagnose_containers.py

# 2. Fix missing containers (creates all 10 required containers)
.\scripts\fix_azure_containers.ps1

# 3. Restart app
az webapp restart --name <webapp-name> --resource-group RG-Zava-Frontend-dev
```

**✅ Fixed in v1.2.5:** Deployment script now validates containers exist before proceeding with data generation

### Agent Not Responding
```bash
# Verify agent ID is set
$env:CUSTOMER_SERVICE_AGENT_ID

# Test Azure connection
az account show

# Check agent in portal
# Visit: https://ai.azure.com → Your Project → Agents
```

### Database Connection Errors (General)
```bash
# Test connection
python parcel_tracking_db.py

# Verify Cosmos DB endpoint
echo $env:COSMOS_DB_ENDPOINT

# Check RBAC permissions (Azure deployment)
az role assignment list --assignee <principal-id> --scope <cosmos-resource-id>
```

### Login Issues on Azure Deployment
**Symptom:** "Demo login failed" or "Invalid credentials" after deployment

**Root Cause:** RBAC permissions take 2-5 minutes to propagate after deployment. User initialization may fail initially.

**Solution (Automatic):**
- ✅ **Fixed v1.2.4**: App now auto-initializes users on first startup
- App retries user creation with each login attempt
- Users are automatically created when RBAC permissions become available

**Manual Verification:**
```bash
# Check app logs for initialization messages
az webapp log tail --name <webapp-name> --resource-group RG-Zava-Logistics

# Look for these messages:
# "✅ App startup initialization completed"
# "✅ Initialized N default users"

# Force app restart to retry initialization
az webapp restart --name <webapp-name> --resource-group RG-Zava-Logistics

# Test locally
python test_user_init.py
```

**If Still Failing After 5 Minutes:**
```bash
# Manually run user initialization
$env:PYTHONPATH="$PWD;$PWD\utils\setup"
python utils\setup\setup_users.py
```

### Photo Display Issues
- ✅ **Fixed v1.2.3**: Lodgement photos now included in track_parcel_tool response
- Verify photos exist in database: Check `lodgement_photos` array in parcel document
- Agent instructions updated to acknowledge auto-displayed photos
- Never tell customers to check "internal systems" when photos exist in data

### Import Errors
```bash
# Set PYTHONPATH for local testing
$env:PYTHONPATH="$PWD;$PWD\utils\setup"

# Verify all dependencies installed
pip install -r requirements.txt
```

### RBAC Permission Errors (Azure)
**✅ RBAC permissions are automatically configured by `deploy_to_azure.ps1`**

The deployment script automatically:
- Assigns **Cosmos DB Built-in Data Contributor** role via Bicep template
- Assigns **Cognitive Services OpenAI User** role for Azure OpenAI access
- Assigns **Cognitive Services User** role for Speech & Vision services
- Waits 60 seconds for Azure RBAC replication across regions
- **Restarts App Service to refresh managed identity credentials** (prevents "Unauthorized" errors on first use)
- Retries user initialization if permissions aren't immediately available

**Why the restart is needed:**
When App Service starts, it caches the managed identity token. If RBAC permissions haven't propagated yet, the cached token lacks necessary permissions. The automatic restart after RBAC assignment ensures fresh credentials with proper access.

**Common symptoms this fixes:**
- "Unauthorized" errors when accessing driver manifest page
- "The input authorization token can't serve the request" errors
- MAC signature verification failures on Cosmos DB operations

**If you still see permission errors after deployment:**
```bash
# Wait additional time (RBAC can take up to 5 minutes to fully propagate)
Start-Sleep -Seconds 120

# Restart the web app to refresh managed identity credentials
az webapp restart --name <webapp-name> --resource-group RG-Zava-Frontend-dev

# Verify role assignments exist
az cosmosdb sql role assignment list \
  --account-name <cosmos-account-name> \
  --resource-group RG-Zava-Backend-dev
```

**Note:** All identity management is consolidated in the Bicep template (`infra/main.bicep`) and deployment script. No manual role assignments should be necessary.

## Workflows

### Multi-Agent Workflow: Fraud Detection → Customer Notification
Located: `workflows/fraud_to_customer_service.py`

**Sequence:**
1. Fraud Detection Agent analyzes suspicious activity
2. If risk ≥70%: Customer Service Agent generates warning
3. If risk ≥85%: Identity Verification Agent triggered
4. If risk ≥90%: Parcel automatically held
5. Customer notified via SMS/email
6. Complete audit trail logged

**Trigger:**
```python
from workflows.fraud_to_customer_service import fraud_detection_to_customer_service_workflow
# Or use the new application layer
from src.application.commands import ReportFraudCommand
from src.infrastructure.database.repositories import ApprovalRepository

# Old way (direct workflow)
result = await fraud_detection_to_customer_service_workflow(
    message_content="Suspicious delivery request",
    customer_name="John Smith",
    customer_email="john@example.com",
    customer_phone="+61400000000"
)

# New way (CQRS pattern)
command = ReportFraudCommand(repository)
await command.execute(message_content="Suspicious delivery request", customer_name="John Smith")
```

## Updating Agents

### Pre-Deployment Validation ✨ NEW

**Always validate agent skills before deployment:**
```bash
# Validate all agent prompts load correctly
python scripts/validate_agent_skills.py

# Expected output:
# ✅ SUCCESS: All 9 agents validated successfully
#
# Deployment Status:
#   ✓ All system-prompt.md files exist and are loadable
#   ✓ Scripts can import from src.infrastructure.agents.core.prompt_loader
#   ✓ Agent prompts will be registered with Azure AI Foundry on deployment
```

**What this validates:**
- ✅ All 9 agent skill folders exist
- ✅ All `system-prompt.md` files are present and valid
- ✅ Import paths work correctly
- ✅ Prompts contain sufficient content (>100 chars)
- ✅ No file system errors

### Update Agent Instructions

**✨ NEW: Edit Markdown Files (Recommended)**
```bash
# Edit the system prompt file directly
# File: src/infrastructure/agents/skills/{agent-name}/system-prompt.md

# Changes take effect immediately on next agent call
# No code changes or redeployment needed!
```

**Example: Update Customer Service Agent**
```bash
# 1. Edit the prompt file
code src/infrastructure/agents/skills/customer-service/system-prompt.md

# 2. Validate changes
python scripts/validate_agent_skills.py

# 3. For Azure deployment, re-register the agent
python scripts/create_foundry_agents_openai.py

# 4. Changes apply immediately (prompts are loaded dynamically)
# Test the updated agent
python test_agent.py customer-service
```

**Alternative Methods:**

**Method 1: Local Testing (Immediate Effect)**
```bash
# Edit src/infrastructure/agents/skills/{agent-name}/system-prompt.md
# Restart your application to pick up changes
```

**Method 2: Register with Azure AI Foundry (Persistent)**
```bash
# After editing system-prompt.md files, register with Azure
python scripts/register_agent_tools_openai.py
```

**Method 3: Update in Azure Portal**
```bash
# Visit: https://ai.azure.com → Your Project → Agents → Edit
# Note: Local system-prompt.md files will override on next registration
```

### Add New Agent Tools
```bash
# 1. Define tool in src/infrastructure/agents/tools/cosmos_tools.py
async def new_tool(param: str) -> str:
    """Tool description"""
    # Implementation using repository pattern
    from src.infrastructure.database.repositories import ParcelRepository
    # ... implementation
    pass

# 2. Add to AGENT_TOOLS list in the same file
AGENT_TOOLS = [
    existing_tools,
    {
        "type": "function",
        "function": {
            "name": "new_tool",
            "description": "Tool description",
            "parameters": {...}
        }
    }
]

# 3. Register with agent
python scripts/register_agent_tools_openai.py
```

## Key Files Reference

### New Enterprise Structure (v2.0+)

| File | Purpose |
|------|---------|
| `src/infrastructure/agents/core/base.py` | Core agent implementations (most agents) |
| `src/infrastructure/agents/core/fraud.py` | Fraud detection agent |
| `src/infrastructure/agents/core/manifest.py` | Dispatcher/manifest agent |
| `src/infrastructure/agents/tools/cosmos_tools.py` | Cosmos DB function tools for agents |
| `src/infrastructure/agents/skills/` | Agent system prompts and capabilities |
| `src/domain/models/` | Business entities (Parcel, Manifest, Driver, etc.) |
| `src/domain/services/` | Business logic services |
| `src/infrastructure/database/cosmos_client.py` | Cosmos DB client |
| `src/infrastructure/database/repositories/` | Data access layer (Repository pattern) |
| `src/interfaces/web/app.py` | Flask application factory |
| `src/interfaces/web/routes/` | Web route blueprints (7 modules) |
| `app.py` | Thin wrapper (26 lines) - entry point |
| `main.py` | CLI interface (uses archived modules) |
| `scripts/register_agent_tools_openai.py` | Register tools with Azure AI agents |
| `scripts/create_foundry_agents_openai.py` | Create agents in Azure AI Foundry |
| `deploy_to_azure.ps1` | Azure deployment automation |
| `workflows/fraud_to_customer_service.py` | Multi-agent workflow |

### Legacy Files (Archived)

| File | New Location |
|------|-------------|
| `agents/base.py` | `src/infrastructure/agents/core/base.py` |
| `agents/fraud.py` | `src/infrastructure/agents/core/fraud.py` |
| `agent_tools.py` | `src/infrastructure/agents/tools/cosmos_tools.py` |
| `parcel_tracking_db.py` | `src/infrastructure/database/cosmos_client.py` |
| `logistics_*.py` (12 files) | `archive/legacy_modules/` (business logic → `src/domain/services/`) |
| `app.py` (5,403 lines) | `archive/app.py.old` (routes → `src/interfaces/web/routes/`) |

### Core Documentation
- `readme.md` - User-focused overview
- `AGENTS.md` - This file (developer/agent focused)
- `README_NEW_STRUCTURE.md` - Quick start guide for new structure
- `RESTRUCTURE_COMPLETE.md` - Complete restructuring report

### Architecture & Development
- `docs/ARCHITECTURE.md` - System architecture (Clean Architecture + DDD)
- `docs/DEVELOPMENT.md` - Developer setup and workflow guide
- `docs/TESTING.md` - Testing strategy and best practices
- `docs/README.md` - Documentation index

### User Guides
- `docs/DEMO_GUIDE.md` - Demo walkthrough
- `docs/APPROVAL_DEMO_GUIDE.md` - Approval agent mode demo (detailed)
- `docs/APPROVAL_DEMO_QUICK_REFERENCE.md` - Approval demo quick reference card
- `docs/AZURE_DEPLOYMENT.md` - Deployment details
- `docs/DISPATCHER_AGENT_GUIDE.md` - Dispatcher integration
- `docs/AGENT_COMMUNICATION_OPPORTUNITIES.md` - Workflow opportunities

### Migration Guides
- `RESTRUCTURE_PLAN.md` - Original restructuring plan
- `ROUTE_MIGRATION_SUMMARY.md` - Where all 53 routes went
- `BLUEPRINT_IMPLEMENTATION_GUIDE.md` - Blueprint development patterns
- `PHASE_1_2_REFACTORING_SUMMARY.md` - Services & agents migration details

## Security Considerations

### Never Commit
- `.env` file with secrets
- Azure connection strings
- API keys
- Agent IDs (except as examples)

### Use Managed Identity
- Preferred for Azure deployments
- Set `USE_MANAGED_IDENTITY=true`
- No keys stored in environment variables
- RBAC roles automatically configured

### Sensitive Data
- Customer PII encrypted at rest
- Audit trail for all operations
- GDPR compliance features
- Photo data stored as base64 in Cosmos DB

## Performance Tips

### Database Optimization
- Use partition keys correctly (`store_location` for parcels, `barcode` for events)
- Batch operations when possible
- Avoid cross-partition queries

### Agent Optimization
- Keep prompts concise and focused
- Use context parameter for additional data
- Cache agent responses when appropriate
- Monitor RU consumption in Cosmos DB

### Azure App Service
- Use B2 or higher SKU for production
- Enable "Always On" for consistent performance
- Monitor Application Insights for bottlenecks
- Scale workers based on load

## Version History

- **v2.0.0** (2026-04-03): Enterprise restructuring - Clean Architecture + DDD implementation
  - Split 5,403-line monolithic app.py into 7 focused blueprints
  - Created domain models, services, and repositories
  - Implemented CQRS pattern with commands and queries
  - Reorganized agents into proper infrastructure layer
  - Added comprehensive test suite (40 test cases)
  - Created 15+ documentation files
- **v1.2.4** (2026-02-12): Fixed Azure deployment login issues with automatic user initialization
- **v1.2.3** (2026-01-13): Fixed lodgement photo display in Customer Service Agent
- **v1.2.0** (2025-12-18): Added 8 active AI agents with performance dashboard
- **v1.1.0** (2025-12): Multi-agent workflows and fraud detection
- **v1.0.0** (2025-11): Initial release with core tracking features

---

**Last Updated:** April 3, 2026 (v2.0.0 - Enterprise Restructuring Complete)
**Agent Framework:** Azure AI Foundry (Microsoft Agent Framework)
**Architecture:** Clean Architecture + Domain-Driven Design
**Maintained By:** Darren Turchiarelli (Microsoft Australia)
