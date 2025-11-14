# Quick Start Guide for Azure Cosmos DB Integration

## Steps to Get Started

### 1. Create Azure Cosmos DB Account (If you don't have one)

```bash
# Using Azure CLI
az cosmosdb create \
    --resource-group your-resource-group \
    --name your-cosmos-account \
    --kind GlobalDocumentDB \
    --locations regionName=East US \
    --default-consistency-level Session \
    --enable-automatic-failover true
```

### 2. Get Your Connection Details

1. Go to Azure Portal → Your Cosmos DB Account → Keys
2. Copy:
   - URI (Cosmos DB endpoint)
   - PRIMARY KEY

### 3. Setup Environment Variables

Create or update your `.env` file:

```env
AZURE_AI_PROJECT_ENDPOINT = "your-ai-foundry-endpoint"
AZURE_AI_MODEL_DEPLOYMENT_NAME = "gpt-4o"

# Azure Cosmos DB Configuration
COSMOS_DB_ENDPOINT = "https://your-cosmos-account.documents.azure.com:443/"
COSMOS_DB_KEY = "your-primary-key-here"
COSMOS_DB_DATABASE_NAME = "agent_workflow_db"
```

### 4. Test Your Setup

Run the setup script to create database and test data:

```bash
python cosmosdb_setup.py
```

### 5. Try the Barcode Scanner Demo

```bash
python barcode_scanner_cosmosdb_demo.py
```

### 6. Run the Agent Workflow

```bash
python Scripts/W04_Sequential_Workflow_Human_Approval.py
```

## Key Benefits of Cosmos DB vs JSON Files

✅ **Scalability**: Handles millions of records
✅ **Reliability**: Built-in backups and high availability
✅ **Performance**: Global distribution and fast queries
✅ **Flexibility**: Supports both structured and unstructured data
✅ **Security**: Enterprise-grade security features
✅ **Integration**: Native Azure integration

## Example Data Structure

### Scanned Item (Package)
```json
{
  "id": "abc123-def456",
  "barcode": "PKG654321",
  "item_name": "Medical Supplies Package",
  "sender_name": "HealthCorp Distribution", 
  "recipient_name": "City General Hospital",
  "recipient_address": "123 Medical Center Dr, Healthcare City, HC 12345",
  "item_type": "medical_supplies",
  "weight": 2.5,
  "dimensions": "30x20x15cm",
  "special_instructions": "Temperature sensitive - keep refrigerated",
  "scan_timestamp": "2024-11-14T12:00:00Z",
  "status": "scanned",
  "tracking_number": "EXP87654321A"
}
```

### Approval Request
```json
{
  "id": "req789-xyz012", 
  "item_barcode": "PKG654321",
  "request_type": "priority_shipping",
  "description": "Request priority shipping for Medical Supplies Package",
  "priority": "high",
  "requested_by": "system_agent",
  "status": "pending",
  "request_timestamp": "2024-11-14T12:00:00Z"
}
```

## Cost Optimization Tips

- Start with 400 RU/s for development
- Use autoscale for production workloads
- Monitor RU consumption in Azure Portal
- Consider serverless tier for variable workloads

## Next Steps

1. Setup your Cosmos DB account
2. Configure environment variables  
3. Run the setup script
4. Test with barcode scanner demo
5. Run the full agent workflow
6. Scale up for production use

Need help? Check README_CosmosDB.md for detailed documentation!