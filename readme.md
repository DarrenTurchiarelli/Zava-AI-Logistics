# 📦 DT Logistics - Last Mile Parcel Tracking System

A modern, AI-powered parcel tracking system for last-mile logistics operations built with **Azure AI Foundry**, **Microsoft Agent Framework**, and **Azure Cosmos DB**. Features intelligent workflow automation, voice-enabled customer service, Azure Maps route optimization, and proactive fraud detection with agent-to-agent communication.

## ⭐ **Latest Updates** ⭐

**December 17, 2025**
- ✅ **ChatGPT-Style UI**: Modern chat bubbles with typing indicators
- ✅ **Conversational AI**: "Alex" agent with natural language responses
- ✅ **Voice Selection**: Fixed voice persona selection for Azure Speech
- ✅ **State Filter**: Shows only valid Australian states (NSW, VIC, QLD, etc.)
- ✅ **Bug Fixes**: Removed deprecated Cosmos DB parameters
- ✅ **Agent Workflows**: Fraud → Customer Service automated escalation
- ✅ **Azure Maps**: Real-time route optimization with traffic analysis

## 🚀 Quick Start

### **Web Application (Recommended)**

```powershell
cd c:\Workbench\dt_item_scanner
$env:FLASK_ENV='development'; py app.py
```

Access at: **http://127.0.0.1:5000**

**Default Login:**
- Username: `admin`
- Password: `admin123`

### **Command-Line Interface**

```powershell
python main.py
```

---

## 🌐 Web Application Features

### **📊 Dashboard**
- Real-time parcel statistics and metrics
- Pending approval counts
- Recent activity feed
- System status monitoring
- Auto-refresh every 30 seconds

### **📦 Parcel Management**
- **Register New Parcels**: Multi-section form with complete details
- **Track Parcels**: Search by tracking number with full history
- **View All Parcels**: Comprehensive listing with sorting/filtering
- **Real-time Updates**: Live tracking information

### **🚗 Driver Manifest System**
- **Azure Maps Route Optimization**: Real-time traffic analysis
- **Automated Route Planning**: Up to 20 parcels per driver with optimized sequence
- **Interactive Maps**: Embedded Azure Maps with route visualization
- **Proof of Delivery**: Mobile-friendly interface for drivers
- **Admin Dashboard**: View all active manifests with progress tracking

### **🎙️ Voice-Enabled Customer Service**
- **Azure Speech Services Integration**: Voice input and output
- **AI-Powered Chatbot**: Customer service agent assistance
- **Public Chat Widget**: Available on all pages for visitors
- **Multi-modal Input**: Type or speak your questions

### **🛡️ Intelligent Fraud Detection**
- **AI Risk Analysis**: Azure AI Foundry fraud detection
- **Automated Workflows**: High-risk fraud → Customer Service escalation
- **Multi-Channel Notifications**: Email, SMS, phone warnings
- **OCR Support**: Extract text from screenshots
- **Email Analysis**: Upload .EML or .MSG files for scanning
- **Identity Verification**: For very high-risk cases (≥85% risk score)
- **Automatic Parcel Holds**: Critical fraud cases (≥90% risk score)

### **📱 Responsive Design**
- Mobile-friendly interface
- Touch-optimized controls
- Works on tablets and smartphones
- Progressive web app capabilities

---

## 🏗️ Architecture & Project Structure

### **Modern Package Organization**

```
dt_item_scanner/
├── agents/               # AI agent implementations
│   ├── base.py          # Core AI agents (Customer Service, Identity)
│   ├── fraud.py         # Fraud detection agent
│   └── manifest.py      # Manifest generation agent
│
├── workflows/           # Agent-to-agent communication workflows
│   └── fraud_to_customer_service.py  # Automated fraud escalation
│
├── services/            # External service integrations
│   ├── maps.py         # Azure Maps route optimization
│   └── speech.py       # Azure Speech Services (voice I/O)
│
├── config/              # Configuration management
│   ├── company.py      # Centralized company branding
│   └── depots.py       # Depot configuration
│
├── utils/               # Shared utilities
│
├── templates/           # Jinja2 HTML templates
├── static/              # CSS, JavaScript, images
│
├── app.py              # Flask web application (main entry)
├── main.py             # CLI interface
├── parcel_tracking_db.py  # Cosmos DB operations
└── requirements.txt    # Python dependencies
```

### **Core Application Modules**

**Entry Points:**
- `app.py` - Flask web application with all routes
- `main.py` - Command-line interface with menu system

**Logistics Operations:**
- `logistics_core.py` - Parcel registration, tracking, scanning
- `logistics_customer.py` - Customer experience features
- `logistics_driver.py` - Driver operations and proof of delivery
- `logistics_depot.py` - Depot management and manifests
- `logistics_ai.py` - AI insights and route optimization
- `logistics_admin.py` - Administration and approvals
- `logistics_common.py` - Shared utilities and helpers

### **Key Benefits**
- **Modular Design**: Clear separation of concerns
- **Easy Maintenance**: Changes isolated to specific packages
- **Scalable**: Add new agents/workflows without affecting existing code
- **Testable**: Each package can be tested independently
- **Reusable**: Components shared across web and CLI interfaces

---

## 🤖 AI-Powered Intelligent Logistics

### **9 Specialized Azure AI Agents**

All agents integrated with **Azure AI Foundry** providing full telemetry and monitoring.

#### **Core Workflow Agents**
1. **Parcel Intake Agent** - Data validation and quality control
2. **Sorting Facility Agent** - Route optimization and exception management
3. **Delivery Coordination Agent** - Resource management and approvals

#### **Enhanced Operations Agents**
4. **Dispatcher Agent** - Capacity optimization and SLA management
5. **Driver Agent** - Real-time execution and proof validation
6. **Optimization Agent** - Predictive analytics and continuous improvement
7. **Customer Service Agent** - Omnichannel communication
8. **Fraud & Risk Agent** - Security and scam detection
9. **Identity Agent** - Authentication and verification

### **🔄 Agent Workflows (NEW)**

**Fraud → Customer Service Escalation**
- Automatic detection of high-risk fraud (score ≥ 70%)
- Personalized customer warnings via Customer Service Agent
- Multi-channel notifications (email, SMS, phone)
- Identity verification for very high risk (≥ 85%)
- Automatic parcel holds for critical cases (≥ 90%)
- Complete audit trail with workflow logging

**Future Workflows** (Planned)
- Exception Resolution → Multi-Agent Coordination
- Delivery Failure → Smart Retry Workflow
- Route → Driver → Customer Pipeline

### **View Telemetry**
1. Visit: https://ai.azure.com
2. Select your Azure AI Foundry project
3. Navigate to: Tracing / Monitoring
4. View: Agent invocations, thread IDs, and performance metrics

---







## 📦 Logistics Workflow

1. **Store Intake** → Parcels registered at collection points
2. **AI Validation** → Parcel Intake Agent validates data quality
3. **Sorting** → Sorting Facility Agent optimizes routing
4. **Assignment** → Dispatcher Agent creates optimized manifests
5. **Delivery** → Driver Agent tracks real-time execution
6. **Confirmation** → Proof of delivery with photo verification
7. **Feedback** → Customer satisfaction tracking

## 💻 Usage Examples

### **Web Interface**

1. **Register a Parcel**: Navigate to Parcels → Register New Parcel
2. **Track Parcel**: Use tracking number in Track Parcel page
3. **Report Fraud**: Submit suspicious messages for AI analysis
4. **Create Manifest**: Admin → Generate Manifest with route optimization
5. **Voice Chat**: Use microphone icon in chatbot for voice input

### **Command-Line Interface**

```bash
python main.py
```

Menu-driven interface for:
- Parcel registration and tracking
- Location-aware scanning
- AI agent workflows
- Test data generation
- Administrative functions

---

## 📊 Database Architecture

**Database**: `agent_workflow_db`

### Containers & Partition Strategy

#### 1. Parcels Container (Partition Key: `/store_location`) 
- Comprehensive parcel data with sender/recipient details
- Tracking numbers, barcodes, and status information
- Service types (standard, express, overnight, registered)
- Special handling requirements

#### 2. Tracking Events Container (Partition Key: `/barcode`)
```json
{
  "id": "abc123-def456",
  "barcode": "LP654321",
  "tracking_number": "LP87654321AB",
  "sender_name": "TechMart Electronics",
  "sender_address": "45 Collins Street, Melbourne CBD, Melbourne VIC 3000",
  "sender_phone": "+61 3 9123 4567",
  "recipient_name": "Sarah Johnson",
  "recipient_address": "123 George Street, Sydney CBD, Sydney NSW 2000",
  "recipient_phone": "+61 2 8765 4321",
  "destination_postcode": "2000",
  "destination_state": "NSW",
  "service_type": "express",
  "weight": 1.2,
  "dimensions": "25x20x8cm",
  "declared_value": 299.99,
  "special_instructions": "Fragile electronics - handle with care",
  "store_location": "Store_Melbourne_CBD",
  "registration_timestamp": "2024-11-14T10:30:00Z",
  "current_status": "registered",
  "current_location": "Store_Melbourne_CBD",
  "estimated_delivery": "2024-11-16T17:00:00Z",
  "delivery_attempts": 0,
  "is_delivered": false
}
```

- Complete event history for each parcel
- Location updates and status changes
- Scanner operations and timestamps

#### 3. Approvals Container (Partition Key: `/barcode`)
- Human approval workflows
- Exception handling requests
- Priority-based processing
- Audit trail with comments

## 🛠️ Setup Instructions

### 1. Prerequisites

- Python 3.11 or later
- Azure subscription with Azure AI Foundry and Cosmos DB services
- Azure CLI (for authentication)

### 2. Azure Cosmos DB Setup

1. Create a new Azure Cosmos DB account:
   - Choose **Core (SQL)** API
   - Select **Serverless** tier for development
   - Note down the endpoint and primary key

### 3. Azure AI Foundry Setup

1. Create an Azure AI Foundry project
2. Deploy a GPT-4o model
3. Note down the project endpoint and connection string

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
# Azure AI Foundry Configuration
AZURE_AI_PROJECT_CONNECTION_STRING = "your-azure-ai-project-connection-string"
AZURE_AI_MODEL_DEPLOYMENT_NAME = "gpt-4o"

# Azure Cosmos DB Configuration (Local Development)
COSMOS_CONNECTION_STRING = "AccountEndpoint=https://your-account.documents.azure.com:443/;AccountKey=your-key-here;"

# Azure Cosmos DB Configuration (Production - Managed Identity)
# USE_MANAGED_IDENTITY = "true"
# COSMOS_DB_ENDPOINT = "https://your-account.documents.azure.com:443/"
# COSMOS_DB_DATABASE_NAME = "logisticstracking"

# Azure Maps (Route Optimization)
AZURE_MAPS_SUBSCRIPTION_KEY = "your-azure-maps-key"

# Azure Speech Services (Voice Features)
AZURE_SPEECH_KEY = "your-speech-key"
AZURE_SPEECH_REGION = "your-region"  # e.g., australiaeast

# Flask Configuration
FLASK_SECRET_KEY = "your-secret-key-for-sessions"
FLASK_ENV = "development"
PORT = 5000
```

**Production Note**: For Azure App Service deployment, use managed identity authentication instead of connection strings. See [DEPLOYMENT.md](Guides/DEPLOYMENT.md#rbac-permissions-required-for-managed-identity) for RBAC setup.

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- `flask>=3.0.0` - Web framework
- `gunicorn>=21.2.0` - Production WSGI server
- `azure-cosmos>=4.5.0` - Cosmos DB client
- `azure-ai-projects>=1.0.0` - Azure AI Foundry SDK
- `azure-cognitiveservices-speech>=1.35.0` - Azure Speech Services (voice)
- `azure-ai-vision-imageanalysis>=1.0.0` - OCR and image analysis
- `python-dotenv>=1.0.0` - Environment variable management
- `pytesseract>=0.3.10` - Text extraction from images

### 6. Generate Demo Data (First-Time Setup)

After deployment or initial setup, generate sample parcels and driver manifests:

```powershell
# Navigate to generators directory
cd utils/generators

# Generate demo manifests for all 57 drivers (30-50 parcels each)
python generate_demo_manifests.py

# OR generate large scalability test for driver-004 (120 parcels)
python generate_demo_manifests.py --large-default

# OR generate custom large manifest
python generate_demo_manifests.py --large 200
```

**What this creates:**
- ✅ Sample parcels distributed across Australian states (NSW, VIC, QLD, SA, WA, ACT)
- ✅ Driver manifests for 57 drivers (driver-001 through driver-057)
- ✅ Realistic Sydney addresses and delivery details
- ✅ Ready-to-use demo environment for testing

**Note**: Run this after every fresh deployment to populate the database with demo data.

### 7. Database Initialization

```bash
# Initialize Cosmos DB with database and containers
python parcel_tracking_db.py
```

This will:
- ✅ Create the `agent_workflow_db` database
- ✅ Create required containers with proper partitioning
- ✅ Add sample test data for demonstration
- ✅ Verify Azure authentication and connectivity

### 8. Start the Application

**Web Interface:**
```powershell
$env:FLASK_ENV='development'; py app.py
```

**CLI Interface:**
```bash
python main.py
```

### 9. RBAC Permissions (Optional - if using Azure AD auth)

```bash
# Assign Cosmos DB roles for Azure AD authentication
az cosmosdb sql role assignment create \
    --account-name your-cosmos-account \
    --resource-group your-resource-group \
    --scope "/" \
    --principal-id your-user-object-id \
    --role-definition-name "Cosmos DB Built-in Data Contributor"
```



## 💻 Usage Examples

### **Web Interface**

1. **Register a Parcel**: Navigate to Parcels → Register New Parcel
2. **Track Parcel**: Use tracking number in Track Parcel page
3. **Report Fraud**: Submit suspicious messages for AI analysis
4. **Create Manifest**: Admin → Generate Manifest with route optimization
5. **Voice Chat**: Use microphone icon in chatbot for voice input

### **Command-Line Interface**

```bash
python main.py
```

Menu-driven interface for:
- Parcel registration and tracking
- Location-aware scanning
- AI agent workflows
- Test data generation
- Administrative functions

## 📋 Service Types & Status Tracking

### Service Types
- **standard** - 5 business day delivery
- **express** - 2 business day delivery  
- **overnight** - Next business day delivery
- **registered** - 3 business day delivery with signature required

### Parcel Statuses
- `registered` - Initial registration at store
- `in_transit` - Moving between facilities
- `at_depot` - Arrived at sorting/distribution facility
- `out_for_delivery` - Assigned to driver for delivery
- `delivered` - Successfully delivered to customer
- `exception` - Issue requiring attention

### Event Types
- `registered` - Parcel entered system
- `in_transit` - Moving between locations
- `at_depot` - Arrived at facility
- `out_for_delivery` - On delivery vehicle
- `delivered` - Successfully delivered
- `delivery_attempt` - Attempted but failed delivery
- `exception` - Issue or problem occurred

## 🔧 API Reference

### Core Parcel Operations
```python
from parcel_tracking_db import ParcelTrackingDB

# Initialize database
async with ParcelTrackingDB() as db:
    # Register new parcel
    parcel = await db.register_parcel(
        barcode="LP123456",
        sender_name="John Smith",
        sender_address="N/A",
        sender_phone=None,
        recipient_name="Jane Doe",
        recipient_address="123 Collins St, Melbourne VIC 3000",
        recipient_phone=None,
        destination_postcode="3000",
        destination_state="VIC",
        service_type="express",
        weight=1.5,
        declared_value=99.99,
        store_location="Store_Melbourne_CBD"
    )

    # Track parcel
    parcel = await db.get_parcel_by_barcode("LP123456")
    tracking_history = await db.get_parcel_tracking_history("LP123456")

    # Update status
    await db.update_parcel_status(
        barcode="LP123456",
        status="out_for_delivery",
        location="Delivery_Vehicle_001",
        scanned_by="driver_001"
    )
```

### Tracking Operations
```python
async with ParcelTrackingDB() as db:
    # Create tracking event
    await db.create_tracking_event(
        barcode="LP123456",
        event_type="in_transit",
        location="Sorting_Facility_VIC",
        description="Parcel sorted for delivery route",
        scanned_by="logistics_001"
    )

    # Filter parcels by store
    store_parcels = await db.get_parcels_by_store("Store_Melbourne_CBD")
    
    # Get store statistics
    stats = await db.get_store_statistics("Store_Melbourne_CBD")
```

### Approval Operations
```python
async with ParcelTrackingDB() as db:
    # Request approval
    request_id = await db.request_approval(
        parcel_barcode="LP123456",
        request_type="delivery_redirect",
        description="Customer requested address change",
        priority="medium"
    )

    # Check status
    status = await db.get_approval_status(request_id)

    # Approve/reject
    await db.approve_request(request_id, "supervisor_001", "Address verified")
    await db.reject_request(request_id, "supervisor_001", "Invalid address")
```

### Synchronous Wrappers (for backwards compatibility)
```python
# Initialize database
db = ParcelTrackingDB()

# Get all parcels
parcels = db.get_all_scanned_items_sync()

# Request approval
request_id = db.request_human_approval_sync("LP123456", "special_handling", "Fragile item")

# Approve request
success = db.approve_request_sync(request_id, "supervisor_001")
```

## 🚦 Exception Handling & Supervisor Approvals

### Approval Request Types
- `exception_handling` - Process delivery exceptions
- `return_to_sender` - Return undeliverable packages
- `delivery_redirect` - Change delivery address
- `damage_claim` - Process damage claims
- `lost_package` - Handle lost package investigations
- `special_handling` - Special handling requirements

### Priority Levels
- `low` - Standard processing
- `medium` - Normal priority
- `high` - Expedited processing
- `critical` - Immediate attention required

## 📈 Performance & Optimization

### Partitioning Strategy
- **Parcels**: Partitioned by store location for operational efficiency
- **Tracking Events**: Partitioned by barcode for query optimization
- **Delivery Attempts**: Partitioned by barcode for approval workflows

### Cost Optimization
- **Development**: Serverless tier for variable workloads
- **Production**: Provisioned throughput with autoscale
- **Indexing**: Optimized for frequently queried fields

### Monitoring Key Metrics
- Request Unit (RU) consumption
- Query performance and latency
- Storage usage and growth patterns
- Error rates and exception handling

## 🔐 Security & Compliance

### Authentication Options
- **Key-based**: Primary/secondary keys (development)
- **Azure AD**: RBAC with built-in data roles (production recommended)
- **Connection security**: TLS encryption for all communications

### Data Protection
- Customer PII encryption at rest and in transit
- Audit trail logging for all operations
- GDPR compliance features
- Data retention policies

## 📁 Project Structure

```
dt_item_scanner/
├── readme.md                                     # This consolidated documentation
├── .env                                          # Environment configuration  
├── requirements.txt                              # Python dependencies
├── parcel_tracking_db.py                        # Consolidated database interface
│
├── 🌐 WEB APPLICATION (Recommended)
├── app.py                                        # Flask web application
├── startup.sh                                    # Azure App Service startup script
├── azure.yaml                                    # Azure deployment configuration
├── deploy_to_azure.ps1                          # Automated deployment script
├── templates/                                    # Jinja2 HTML templates
│   ├── base.html                                # Master layout with navigation
│   ├── index.html                               # Landing page
│   ├── login.html                               # Authentication
│   ├── dashboard.html                           # Operations dashboard
│   ├── register_parcel.html                     # Parcel registration form
│   ├── track_parcel.html                        # Tracking interface
│   ├── all_parcels.html                         # Parcel listing
│   ├── report_fraud.html                        # Fraud reporting with AI
│   ├── approvals.html                           # Approval workflows
│   ├── ai_insights.html                         # Analytics dashboard
│   └── error.html                               # Error pages
├── static/                                       # Frontend assets
│   ├── css/
│   │   └── style.css                            # Custom styling
│   └── js/
│       └── app.js                               # Client-side JavaScript
│
├── 🚀 MODULAR CLI APPLICATION
├── main.py                                       # Entry point and routing
├── logistics_common.py                           # Shared utilities
├── logistics_core.py                            # Core operations
├── logistics_customer.py                        # Customer features
├── logistics_driver.py                          # Driver operations
├── logistics_depot.py                           # Depot management
├── logistics_ai.py                              # AI features
├── logistics_admin.py                           # Admin functions
├── logistics_menu.py                            # Menu system
├── logistics_parcel.py                          # Parcel data models
├── customer_service_chatbot.py                  # AI chatbot agent
│
├── Scripts/                                      # AI Agent Framework
│   ├── A01_Create_Multiple_Foundry_Agent_Persistent.py  # Create logistics agents
│   └── W01_Sequential_Workflow_Human_Approval.py        # Main AI workflow
└── __pycache__/                                 # Python cache files
```

## 🔧 Troubleshooting

### Common Issues

#### "Cannot run the event loop while another loop is running"
This error occurs when AI agents try to use sync database methods within async context.
**Solution**: The current system uses mock agent tools to avoid this issue. Real database operations happen at the workflow level.

#### Authentication Errors
```bash
# Error: "Local Authorization is disabled"
# Solution: Use Azure AD authentication or enable key-based auth
az cosmosdb update --name your-account --resource-group your-rg --disable-local-auth false
```

#### Partition Key Errors
- Ensure store_location is provided for parcel operations
- Use barcode for tracking events and delivery attempts

#### Performance Issues
- Monitor RU consumption in Azure Portal
- Optimize query patterns to avoid cross-partition queries
- Consider increasing provisioned throughput

### Debug Tools
```bash
# Test database connectivity and setup
python Identity_Test_CosmosDB_connection.py

# Initialize and test database with sample data
python parcel_tracking_db.py

# Enable debug logging (if needed)
export AZURE_LOG_LEVEL=DEBUG
```

## 🔄 Migration & Integration

### Consolidated Architecture
The system now uses a single consolidated database interface (`parcel_tracking_db.py`) that combines:
- All Cosmos DB operations
- Setup and testing utilities  
- Synchronous wrappers for backwards compatibility
- Australian localization features

### External System Integration
- REST APIs for real-time tracking
- Webhook notifications for status changes
- Bulk upload APIs for batch operations
- Integration with store POS systems and driver mobile apps

## 📊 Service Types & Status Tracking

### **Service Types**
- **Standard** - 5 business day delivery
- **Express** - 2 business day delivery
- **Overnight** - Next business day delivery
- **Registered** - 3 business day delivery with signature required

### **Parcel Statuses**
- `registered` - Initial registration at store
- `in_transit` - Moving between facilities
- `at_depot` - At sorting/distribution facility
- `out_for_delivery` - Assigned to driver
- `delivered` - Successfully delivered
- `exception` - Issue requiring attention

---

## 🔧 API & Integration

### **Cosmos DB Operations**

```python
from parcel_tracking_db import ParcelTrackingDB

async with ParcelTrackingDB() as db:
    # Register parcel
    parcel = await db.register_parcel(
        barcode="LP123456",
        recipient_name="Jane Doe",
        recipient_address="123 Collins St, Melbourne VIC 3000",
        destination_postcode="3000",
        destination_state="VIC",
        service_type="express",
        weight=1.5,
        store_location="Store_Melbourne_CBD"
    )
    
    # Track parcel
    tracking_history = await db.get_parcel_tracking_history("LP123456")
    
    # Update status
    await db.update_parcel_status(
        barcode="LP123456",
        status="out_for_delivery",
        location="Delivery_Vehicle_001"
    )
```

### **Agent Integration**

```python
from agents.fraud import fraud_risk_agent
from agents.base import customer_service_agent

# Analyze fraud
result = await fraud_risk_agent({
    "message": "Suspicious delivery request",
    "sender": "unknown@example.com"
})

# Get customer service response
response = await customer_service_agent({
    "query": "Where is my parcel?",
    "tracking_number": "LP123456"
})
```

### **Workflow Automation**

```python
from workflows.fraud_to_customer_service import fraud_detection_to_customer_service_workflow

# Trigger fraud → customer service workflow
workflow_result = await fraud_detection_to_customer_service_workflow(
    message_content="Suspicious SMS about delivery fees",
    customer_name="John Smith",
    customer_email="john@example.com"
)
```

---

## 🚀 Deployment

### **Azure App Service**

```powershell
# Deploy using Azure CLI
az webapp up --runtime PYTHON:3.11 --sku B1 --name dt-logistics-web
```

See `Guides/DEPLOYMENT.md` for complete instructions including:
- Environment variable configuration
- CI/CD setup
- Monitoring and logging
- Scaling options

---

## 🔧 Troubleshooting

### **Common Issues**

**Database Connection Errors**
```bash
# Test Cosmos DB connectivity
python parcel_tracking_db.py
```

**Agent Not Responding**
```bash
# Verify Azure credentials
az login

# Check .env configuration
cat .env | Select-String "AZURE"
```

**Speech/Voice Features Not Working**
- Verify `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` in `.env`
- Check microphone permissions in browser
- Test with `services/speech.py`

**Azure Maps Not Optimizing Routes**
- Validate `AZURE_MAPS_SUBSCRIPTION_KEY`
- Run `Test Scripts/test_azure_maps.py`
- Check API quota limits

---

## 📚 Additional Resources

- [Azure AI Foundry Documentation](https://learn.microsoft.com/en-us/azure/ai-studio/)
- [Azure Cosmos DB Documentation](https://docs.microsoft.com/en-us/azure/cosmos-db/)
- [Azure Maps Documentation](https://docs.microsoft.com/en-us/azure/azure-maps/)
- [Azure Speech Services Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/)

---

## 📄 License

This project uses Azure AI services and follows Microsoft licensing terms.

---

**🚀 Get Started Now:**
1. Configure `.env` with Azure credentials
2. Run `python parcel_tracking_db.py` to initialize database
3. Start web app: `$env:FLASK_ENV='development'; py app.py`
4. Access http://127.0.0.1:5000 (Login: admin/admin123)

Experience the complete AI-powered logistics system with voice features, fraud detection workflows, and real-time route optimization! 
