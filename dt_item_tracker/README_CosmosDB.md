# Azure Cosmos DB Integration for Agent Framework

This implementation replaces the previous JSON file-based system with Azure Cosmos DB for storing scanned barcode items and approval requests. Cosmos DB provides scalability, reliability, and flexibility for both structured and unstructured data.

## Architecture Overview

### Database Structure

**Database**: `agent_workflow_db`

**Containers**:
1. **scanned_items** (Partition Key: `/item_type`)
   - Stores information about scanned barcode items
   - Includes sender, recipient, address, and shipping details
   
2. **approval_requests** (Partition Key: `/request_type`)
   - Stores human approval requests for various actions
   - Tracks approval status and comments

### Data Models

#### Scanned Item Document
```json
{
  "id": "uuid",
  "barcode": "PKG123456",
  "item_name": "Medical Supplies Package",
  "sender_name": "HealthCorp Distribution",
  "recipient_name": "City General Hospital",
  "recipient_address": "123 Medical Center Dr, Healthcare City, HC 12345",
  "item_type": "medical_supplies",
  "weight": 2.5,
  "dimensions": "30x20x15cm",
  "special_instructions": "Temperature sensitive - keep refrigerated",
  "scan_timestamp": "2024-01-01T12:00:00Z",
  "status": "scanned",
  "tracking_number": "EXP12345678A"
}
```

#### Approval Request Document
```json
{
  "id": "uuid",
  "item_barcode": "PKG123456",
  "request_type": "priority_shipping",
  "description": "Request priority shipping for Medical Supplies Package",
  "priority": "high",
  "requested_by": "system_agent",
  "status": "pending",
  "request_timestamp": "2024-01-01T12:00:00Z",
  "approved_by": null,
  "approval_timestamp": null,
  "comments": null
}
```

## Setup Instructions

### 1. Create Azure Cosmos DB Account

1. Go to the [Azure Portal](https://portal.azure.com)
2. Create a new Cosmos DB account:
   - Choose **Core (SQL)** API
   - Select your subscription and resource group
   - Choose a unique account name
   - Select a region close to your location
   - Choose **Provisioned throughput** for cost predictability

### 2. Get Connection Details

1. Once the Cosmos DB account is created, go to the **Keys** section
2. Copy the following values:
   - **URI** (Cosmos DB endpoint)
   - **PRIMARY KEY**

### 3. Configure Environment Variables

1. Copy `env_template.txt` to `.env`
2. Update the `.env` file with your Cosmos DB details:

```env
AZURE_AI_PROJECT_ENDPOINT = "<AZURE AI FOUNDRY PROJECT ENDPOINT>"
AZURE_AI_MODEL_DEPLOYMENT_NAME = "<gpt-4o>"

# Azure Cosmos DB Configuration
COSMOS_DB_ENDPOINT = "https://your-cosmos-account.documents.azure.com:443/"
COSMOS_DB_KEY = "your-primary-key-here"
COSMOS_DB_DATABASE_NAME = "agent_workflow_db"
```

### 4. Install Dependencies

```bash
pip install -r cosmosdb_requirements.txt
```

### 5. Initialize Database

Run the setup script to create the database and containers:

```bash
python cosmosdb_setup.py
```

Choose option 1 to setup Cosmos DB with test data.

## Usage

### Barcode Scanner Demo

Use the barcode scanner demo to simulate scanning items:

```bash
python barcode_scanner_cosmosdb_demo.py
```

This provides an interactive interface to:
- Scan items manually
- Add sample items for testing
- View recently scanned items
- Search items by barcode

### Agent Workflow

The main workflow script has been updated to use Cosmos DB:

```bash
python Scripts/W04_Sequential_Workflow_Human_Approval.py
```

## API Reference

### Core Functions

#### Scanned Items
- `add_scanned_item()` - Add a new scanned item
- `get_all_scanned_items()` - Retrieve all scanned items
- `get_scanned_item_by_barcode()` - Find item by barcode
- `update_scanned_item_status()` - Update item status

#### Approval Requests
- `request_human_approval()` - Create approval request
- `get_human_approval_status()` - Check approval status
- `get_all_pending_approvals()` - Get pending requests
- `approve_request()` - Approve a request
- `reject_request()` - Reject a request

#### Utility Functions
- `add_random_scanned_items()` - Generate test data
- `add_random_approval_requests()` - Generate test approvals
- `cleanup_database()` - Remove all data (testing)

### Synchronous Wrappers

For compatibility with the existing agent framework, synchronous wrapper functions are provided:
- `get_all_scanned_items_sync()`
- `add_scanned_item_sync()`
- `request_human_approval_sync()`
- etc.

## Item Types

The system supports various item types:
- `package` - General packages
- `document` - Legal/official documents
- `equipment` - Industrial equipment and components
- `medical_supplies` - Medical and pharmaceutical items
- `electronics` - Electronic devices and components

## Priority Levels

Approval requests can have different priority levels:
- `low` - Standard processing
- `medium` - Normal priority
- `high` - Expedited processing
- `critical` - Immediate attention required

## Request Types

Common approval request types:
- `schedule_maintenance` - Equipment maintenance requests
- `immediate_shutdown` - Emergency shutdown procedures
- `priority_shipping` - Expedited shipping requests
- `special_handling` - Items requiring special handling

## Cost Optimization

### Throughput Settings
- Development: 400 RU/s per container (minimum)
- Production: Scale based on usage patterns
- Consider using autoscale for variable workloads

### Partition Strategy
- `scanned_items`: Partitioned by `item_type`
- `approval_requests`: Partitioned by `request_type`
- Ensures even distribution of data and optimal performance

### Indexing
- Default indexing policy is used
- Consider custom indexing for specific query patterns
- Exclude unused properties to reduce storage costs

## Monitoring

### Key Metrics to Monitor
- Request Unit (RU) consumption
- Storage usage
- Query performance
- Error rates

### Azure Portal Monitoring
- Use the Metrics blade in Azure Portal
- Set up alerts for high RU consumption
- Monitor partition hot spots

## Security Best Practices

1. **Connection Strings**: Never commit connection strings to source control
2. **Access Keys**: Rotate keys regularly
3. **Network Security**: Configure firewall rules and VNet integration
4. **RBAC**: Use Azure AD authentication when possible
5. **Encryption**: Data is encrypted at rest and in transit by default

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify endpoint and key are correct
   - Check firewall settings
   - Ensure network connectivity

2. **Throttling (429 errors)**
   - Increase RU/s provisioning
   - Implement retry logic with exponential backoff
   - Optimize query patterns

3. **Partition Hot Spots**
   - Review partition key selection
   - Monitor partition metrics
   - Consider data distribution patterns

4. **High Costs**
   - Review RU/s allocation
   - Optimize query efficiency
   - Consider serverless tier for variable workloads

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export AZURE_LOG_LEVEL=DEBUG
```

## Migration from JSON Files

If migrating from the previous JSON file-based system:

1. Export existing JSON data
2. Transform data to match new schema
3. Import using bulk operations for efficiency
4. Validate data integrity
5. Update all references to use new functions

## Performance Tips

1. **Batch Operations**: Use batch APIs for multiple operations
2. **Query Optimization**: Use proper indexing and filtering
3. **Connection Pooling**: Reuse connections when possible
4. **Async Operations**: Use async/await for better scalability
5. **Caching**: Consider caching frequently accessed data

## Further Reading

- [Azure Cosmos DB Documentation](https://docs.microsoft.com/en-us/azure/cosmos-db/)
- [Python SDK Reference](https://docs.microsoft.com/en-us/python/api/overview/azure/cosmos-db)
- [Best Practices Guide](https://docs.microsoft.com/en-us/azure/cosmos-db/performance-tips)
- [Cost Optimization](https://docs.microsoft.com/en-us/azure/cosmos-db/optimize-cost-throughput)