# Last Mile Logistics Parcel Tracking System

A comprehensive parcel tracking system for last-mile logistics operations using Microsoft Agent Framework and Azure Cosmos DB. This system manages the complete logistics journey from store intake through customer delivery with real-time tracking and AI-powered workflow automation.

## 🚀 System Overview

### Logistics Journey
1. **Store Intake** - Parcels registered when received at stores
2. **Sorting Facility** - Parcels sorted and routed to appropriate facilities
3. **Driver Assignment** - Parcels assigned to delivery drivers
4. **Delivery Attempts** - Multiple delivery attempts with status tracking
5. **Customer Handoff** - Final delivery confirmation and receipt

### Key Features

#### 🏗️ Architecture
- **Azure Cosmos DB**: Scalable NoSQL database for parcel and tracking data
- **Microsoft Agent Framework**: AI-powered workflow automation
- **Real-time Tracking**: GPS-based location updates and status tracking
- **Interactive Demo**: Barcode scanner simulation with Australian localization

#### 📦 Logistics Management
- Comprehensive parcel registration with sender/recipient details
- Support for multiple service types (standard, express, overnight, registered)
- Weight support for both grams and kilograms with automatic conversion
- Australian address format and AUD currency support
- Special handling requirements tracking

#### 🤖 AI Workflow Automation
- **Parcel Intake Agent**: Processes new parcels from stores
- **Sorting Facility Agent**: Handles routing and exceptions
- **Delivery Coordination Agent**: Manages driver assignments and deliveries
- Human approval workflow for critical operations

## 📊 Database Architecture

**Database**: `logistics_tracking_db`

### Containers & Data Models

#### 1. Lodgement Container (Partition Key: `/destination_postcode`)
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

#### 2. Tracking Events Container (Partition Key: `/tracking_number`)
```json
{
  "id": "event789-xyz012",
  "barcode": "LP654321",
  "tracking_number": "LP87654321AB",
  "event_type": "in_transit",
  "location": "Sorting_Facility_NSW",
  "description": "Parcel sorted and loaded for delivery route",
  "scanned_by": "logistics_staff_001",
  "timestamp": "2024-11-14T14:25:00Z",
  "additional_info": {
    "route": "Route_A",
    "driver": "DRV001"
  }
}
```

#### 3. Delivery Attempts Container (Partition Key: `/tracking_number`)
```json
{
  "id": "attempt456-qwe789",
  "barcode": "LP654321",
  "tracking_number": "LP87654321AB",
  "attempt_type": "delivery",
  "status": "failed",
  "driver_id": "DRV001",
  "location": "Customer_Address",
  "timestamp": "2024-11-15T16:45:00Z",
  "reason": "Customer not home",
  "next_attempt_date": "2024-11-16T09:00:00Z"
}
```

## 🛠️ Setup Instructions

### 1. Prerequisites

- Python 3.11 or later
- Azure subscription
- Azure AI Foundry project

### 2. Azure Cosmos DB Setup

1. Create a new Azure Cosmos DB account:
   - Choose **Core (SQL)** API
   - Select **Serverless** tier for development
   - Note down the endpoint and primary key

### 3. Azure AI Foundry Setup

1. Create an Azure AI Foundry project
2. Deploy a GPT-4o model
3. Note down the project endpoint

### 4. Environment Configuration

Copy `env_template.txt` to `.env` and configure:

```env
# Azure AI Foundry Configuration
AZURE_AI_PROJECT_ENDPOINT = "https://your-project.westus.ai.azure.com"
AZURE_AI_MODEL_DEPLOYMENT_NAME = "gpt-4o"

# Azure Cosmos DB Configuration
COSMOS_DB_ENDPOINT = "https://your-cosmos-account.documents.azure.com:443/"
COSMOS_DB_KEY = "your-primary-key-here"
COSMOS_DB_DATABASE_NAME = "logistics_tracking_db"
```

### 5. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Cosmos DB specific dependencies
pip install -r cosmosdb_requirements.txt
```

### 6. Database Initialization

```bash
# Initialize Cosmos DB with sample data
python cosmosdb_setup.py
```

### 7. RBAC Permissions (if using Azure AD auth)

```bash
# Assign Cosmos DB roles for Azure AD authentication
az cosmosdb sql role assignment create \
    --account-name your-cosmos-account \
    --resource-group your-resource-group \
    --scope "/" \
    --principal-id your-user-object-id \
    --role-definition-name "Cosmos DB Built-in Data Contributor"
```

## 🖥️ Usage

### Interactive Barcode Scanner Demo

```bash
python barcode_scanner_cosmosdb_demo.py
```

**Features:**
- ✅ **Register parcels** with interactive prompts
- ✅ **Track parcels** by barcode or tracking number
- ✅ **View recent parcels** with detailed information
- ✅ **Generate sample parcels** for testing
- ✅ **Simulate logistics operations** for demonstration

**Australian Localization:**
- Australian addresses and postcodes
- Phone numbers in +61 format
- Currency in AUD ($)
- Weight input in both grams and kilograms

### AI Agent Workflows

#### Create Persistent Agents

```bash
# Create multiple logistics agents
python Scripts/A03_Create_Multiple_Foundry_Agent_Persistent.py
```

#### Run Sequential Workflow with Human Approval

```bash
# Main workflow with approval checkpoints
python Scripts/W04_Sequential_Workflow_Human_Approval.py
```

**Workflow Features:**
- **Parcel Intake Agent**: Processes new parcels and validates information
- **Sorting Facility Agent**: Handles routing decisions and exceptions
- **Delivery Coordination Agent**: Manages driver assignments and delivery attempts
- **Human Approval**: Critical operations require supervisor approval

## 📋 Service Types & Status Tracking

### Service Types
- **standard** - 5 business day delivery
- **express** - 2 business day delivery  
- **overnight** - Next business day delivery
- **registered** - 3 business day delivery with signature required

### Parcel Statuses
- `registered` - Initial registration at store
- `in_transit` - Moving between facilities
- `at_facility` - Arrived at sorting/distribution facility
- `out_for_delivery` - Assigned to driver for delivery
- `delivered` - Successfully delivered to customer
- `exception` - Issue requiring attention

### Event Types
- `registered` - Parcel entered system
- `in_transit` - Moving between locations
- `at_facility` - Arrived at facility
- `out_for_delivery` - On delivery vehicle
- `delivered` - Successfully delivered
- `delivery_attempt` - Attempted but failed delivery
- `exception` - Issue or problem occurred

## 🔧 API Reference

### Core Parcel Operations
```python
from cosmosdb_tools import *

# Register new parcel
parcel = await register_parcel(
    barcode="LP123456",
    sender_name="John Smith",
    recipient_name="Jane Doe",
    recipient_address="123 Collins St, Melbourne VIC 3000",
    destination_postcode="3000",
    service_type="express",
    weight=1.5,
    declared_value=99.99
)

# Track parcel
parcel = await get_parcel_by_barcode("LP123456")
tracking_history = await get_parcel_tracking_history("LP123456")

# Update status
await update_parcel_status(
    barcode="LP123456",
    status="out_for_delivery",
    location="Delivery_Vehicle_001",
    scanned_by="driver_001"
)
```

### Tracking Operations
```python
# Create tracking event
await create_tracking_event(
    barcode="LP123456",
    event_type="in_transit",
    location="Sorting_Facility_VIC",
    description="Parcel sorted for delivery route",
    scanned_by="logistics_001"
)

# Filter parcels by status
pending_parcels = await get_parcels_by_status("out_for_delivery")
facility_parcels = await get_parcels_by_location("Sorting_Facility_VIC")
```

### Delivery Operations
```python
# Record delivery attempt
await record_delivery_attempt(
    barcode="LP123456",
    attempt_type="delivery",
    status="successful",
    driver_id="DRV001",
    location="Customer_Address",
    recipient_signature="J. Doe"
)

# Get delivery history
attempts = await get_delivery_attempts("LP123456")
driver_deliveries = await get_driver_deliveries("DRV001")
```

### Supervisor Approvals
```python
# Request approval
request_id = await request_supervisor_approval(
    parcel_barcode="LP123456",
    request_type="delivery_redirect",
    description="Customer requested address change",
    priority="medium"
)

# Check status
status = await get_approval_status(request_id)

# Approve/reject
await approve_request(request_id, "supervisor_001", "Address verified")
await reject_request(request_id, "supervisor_001", "Invalid address")
```

## 🚦 Exception Handling & Supervisor Approvals

### Approval Request Types
- `exception_handling` - Process delivery exceptions
- `return_to_sender` - Return undeliverable packages
- `delivery_redirect` - Change delivery address
- `damage_claim` - Process damage claims
- `lost_package` - Handle lost package investigations

### Priority Levels
- `low` - Standard processing
- `medium` - Normal priority
- `high` - Expedited processing
- `critical` - Immediate attention required

## 📈 Performance & Optimization

### Partitioning Strategy
- **Lodgement**: Partitioned by destination postcode for geographic distribution
- **Tracking Events**: Partitioned by tracking number for query optimization
- **Delivery Attempts**: Partitioned by tracking number for operational efficiency

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
dt_item_tracker/
├── README.md                                      # This consolidated documentation
├── .env                                          # Environment configuration
├── requirements.txt                              # Core dependencies
├── cosmosdb_requirements.txt                     # Cosmos DB dependencies
├── cosmosdb_setup.py                            # Database initialization
├── cosmosdb_tools.py                            # Database operations
├── barcode_scanner_cosmosdb_demo.py             # Interactive demo
├── test_cosmos_connection.py                     # Connection testing
├── Scripts/                                      # Agent framework examples
│   ├── A01_Create_Single_Foundry_Agent.py      # Single agent creation
│   ├── A02_Create_Single_Foundry_Agent_Persistent.py
│   ├── A03_Create_Multiple_Foundry_Agent_Persistent.py  # Multiple agents
│   ├── W01_Sequential_Workflow.py              # Sequential workflow
│   ├── W02_Handoff_Workflow.py                # Handoff workflow
│   ├── W03_Magentic_Workflow.py               # Magentic workflow
│   └── W04_Sequential_Workflow_Human_Approval.py  # Main logistics workflow
├── images/                                      # Documentation images
│   ├── seq_workflow_overview.png
│   ├── seq_workflow.png
│   └── seq_workflow_human_approval_overview.png
├── approval_db.json                            # Legacy approval database
├── workflow_checkpoint.json                    # Workflow state management
└── env_template.txt                            # Environment template
```

## 🔧 Troubleshooting

### Common Issues

#### Authentication Errors
```bash
# Error: "Local Authorization is disabled"
# Solution: Use Azure AD authentication or enable key-based auth
az cosmosdb update --name your-account --resource-group your-rg --disable-local-auth false
```

#### Partition Key Errors
- Ensure destination_postcode is provided for parcel operations
- Use tracking_number for tracking events and delivery attempts

#### Performance Issues
- Monitor RU consumption in Azure Portal
- Optimize query patterns to avoid cross-partition queries
- Consider increasing provisioned throughput

### Debug Tools
```bash
# Test Cosmos DB connection
python test_cosmos_connection.py

# Enable debug logging
export AZURE_LOG_LEVEL=DEBUG
```

## 🔄 Migration & Integration

### From JSON to Cosmos DB
The system maintains backward compatibility while providing modern database functionality:

```python
# Legacy JSON approach
with open('approval_db.json', 'r') as f:
    data = json.load(f)

# Modern Cosmos DB approach
parcels = await get_all_parcels()
```

### External System Integration
- REST APIs for real-time tracking
- Webhook notifications for status changes
- Bulk upload APIs for batch operations
- Integration with store POS systems and driver mobile apps

## 🚀 Future Enhancements

### Advanced Features
- Machine learning delivery prediction
- Route optimization algorithms
- Predictive exception handling
- Customer preference learning
- Real-time GPS tracking integration

### Scalability Improvements
- Multi-region deployment
- Automated scaling policies
- Disaster recovery procedures
- Advanced analytics and reporting

## 📚 Additional Resources

- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview)
- [Azure Cosmos DB Documentation](https://docs.microsoft.com/en-us/azure/cosmos-db/)
- [Azure AI Foundry Documentation](https://learn.microsoft.com/en-us/azure/ai-studio/)

## 📄 License

This project follows the Microsoft Agent Framework licensing terms.

---

**Getting Started**: Run `python barcode_scanner_cosmosdb_demo.py` to explore the interactive logistics tracking system with Australian localization! 🇦🇺
