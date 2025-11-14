# Database-Based Approval System

## Overview

This system has been upgraded from using JSON file simulation to a proper database structure for managing scanned barcode items, shipping information, and approval workflows.

## Key Features

### 🗃️ Database Structure
- **SQLite Database**: Local, serverless database for easy deployment
- **Structured Data**: Proper relationships between items, approvals, and equipment
- **Scalable Design**: Can easily be migrated to cloud databases (PostgreSQL, Azure SQL, Cosmos DB)

### 📱 Barcode Scanning Integration
- Support for scanned barcode items with full shipping details
- Sender/recipient information tracking
- Special handling requirements (fragile, temperature-controlled, etc.)
- Weight, dimensions, and package type classification

### 🔄 Approval Workflow
- Automated approval request creation for special handling items
- Human approval interface for critical actions
- Status tracking (pending, approved, rejected)
- Audit trail with timestamps and approver information

## Database Schema

### Tables

1. **scanned_items**
   - Primary item information from barcode scans
   - Sender/recipient details
   - Package specifications (weight, dimensions, type)
   - Special handling requirements

2. **approval_requests**
   - Approval workflow management
   - Links to scanned items
   - Status tracking and approver information
   - Action types and reasons

3. **equipment_maintenance**
   - Equipment status tracking
   - Maintenance scheduling
   - Historical maintenance records

## Quick Start

### 1. Install Dependencies
```bash
cd "Agent Framework"
pip install -r requirements.txt
# Database functionality uses built-in sqlite3
```

### 2. Initialize Database
```python
from database_setup import ApprovalDatabase

# Create and initialize database
db = ApprovalDatabase()
db.add_sample_data()  # Optional: Add sample data for testing
```

### 3. Simulate Barcode Scanning
```bash
python barcode_scanner_demo.py
```

This interactive demo allows you to:
- Simulate scanning new items
- View system dashboard
- Manually approve/reject requests
- See the complete workflow in action

### 4. Run Agent Workflow
```bash
# Update agent IDs in the script first
python Scripts/W04_Sequential_Workflow_Human_Approval.py
```

## Code Examples

### Adding a Scanned Item
```python
from database_tools import add_scanned_item

item_id = add_scanned_item(
    barcode="123456789012",
    item_number="PKG001",
    sender_name="John Smith", 
    recipient_name="Alice Johnson",
    recipient_address="123 Collins Street, Melbourne VIC 3000",
    item_type="electronics",
    weight=2.5,
    special_handling="fragile"
)
```

### Creating Approval Request
```python
from database_tools import request_human_approval

approval_id = request_human_approval(
    action="Process Special Handling",
    equipment_id="scanner_001",
    equipment_type="barcode_scanner",
    item_barcode="123456789012"
)
```

### Checking Approval Status
```python
from database_tools import get_human_approval_status

status = get_human_approval_status(equipment_id="scanner_001")
print(f"Status: {status}")  # [PENDING], [APPROVED], [REJECTED], etc.
```

### Approving/Rejecting Requests
```python
from database_tools import approve_request, reject_request

# Approve
success = approve_request(approval_id=1, approved_by="Manager Smith")

# Reject  
success = reject_request(approval_id=2, rejection_reason="Insufficient documentation")
```

## Agent Integration

The AI agents now work with the database system:

### Data Analyser Agent
- **Tools**: `get_data`, `get_all_equipment_from_approval_db`, `get_all_scanned_items`
- **Function**: Analyzes scanned items and equipment data

### Risk Assessor Agent  
- **Tools**: `request_human_approval`, `get_all_pending_approvals`, `get_all_approved_items`, `add_scanned_item`
- **Function**: Evaluates risk and creates approval requests for critical actions

### Maintenance Scheduler Agent
- **Tools**: All approval management tools plus maintenance actions
- **Function**: Processes approved requests and schedules maintenance/actions

## Migration from JSON System

The system maintains backward compatibility while adding database functionality:

### Before (JSON)
```python
# Old JSON-based approach
approval_json_file = '../approval_db.json'
with open(approval_json_file, 'r') as f:
    data = json.load(f)
```

### After (Database)
```python
# New database approach  
from database_tools import get_all_pending_approvals
pending = get_all_pending_approvals()
```

## Cloud Migration Options

### Option 1: Azure Cosmos DB (Recommended for Azure environments)
```python
from azure.cosmos import CosmosClient

# Replace SQLite with Cosmos DB
client = CosmosClient(endpoint, key)
database = client.get_database_client("approval_system")
```

### Option 2: Azure SQL Database
```python
import pyodbc

# Connection string for Azure SQL
conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=..."
```

### Option 3: PostgreSQL (Azure Database for PostgreSQL)
```python
import psycopg2

# PostgreSQL connection
conn = psycopg2.connect(
    host="your-server.postgres.database.azure.com",
    database="approval_system",
    user="username",
    password="password"
)
```

## File Structure

```
Agent Framework/
├── database_setup.py              # Database schema and initialization
├── database_tools.py              # Tool functions for agents
├── barcode_scanner_demo.py        # Interactive demo
├── database_requirements.txt      # Additional dependencies
├── approval_system.db             # SQLite database file (created automatically)
├── Scripts/
│   └── W04_Sequential_Workflow_Human_Approval.py  # Updated workflow script
└── README_Database.md             # This documentation
```

## Benefits of Database Approach

### ✅ Advantages over JSON File System
1. **Data Integrity**: ACID transactions and constraints
2. **Concurrent Access**: Multiple processes can safely access data
3. **Scalability**: Easy to migrate to cloud databases
4. **Performance**: Indexed queries and optimized storage
5. **Relationships**: Proper foreign key relationships
6. **Audit Trail**: Built-in timestamp and user tracking
7. **Backup/Recovery**: Standard database backup procedures

### 🔧 Operational Improvements
1. **Real-time Updates**: No file locking issues
2. **Query Flexibility**: SQL queries for complex data analysis
3. **Data Validation**: Schema enforcement and type checking
4. **Integration Ready**: Standard database connections for other systems
5. **Monitoring**: Database-level monitoring and logging

## Next Steps

1. **Production Deployment**: Migrate to cloud database for production use
2. **Integration**: Connect to real barcode scanning hardware/software
3. **Authentication**: Add user authentication and role-based access
4. **Reporting**: Build dashboards and analytics
5. **Notifications**: Add email/SMS notifications for approvals
6. **API Layer**: Create REST API for external system integration

## Support

For questions or issues:
1. Check the database connection in `database_setup.py`
2. Run the demo script to verify functionality
3. Check agent logs for workflow issues
4. Ensure all dependencies are installed

## License

This system follows the same license as the parent Agent Framework project.