"""
Initialize Cosmos DB containers with proper partition keys.
Run this with local auth enabled on Cosmos DB.
"""
import asyncio
import os
from dotenv import load_dotenv
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey

load_dotenv()

async def initialize_containers():
    """Create all required Cosmos DB containers"""
    
    # Get connection string from environment
    connection_string = os.getenv("COSMOS_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("COSMOS_CONNECTION_STRING environment variable is required")
    
    # Parse endpoint from connection string
    endpoint = connection_string.split(";")[0].replace("AccountEndpoint=", "")
    key = connection_string.split(";")[1].replace("AccountKey=", "")
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "logisticstracking")
    
    print(f"🔧 Initializing Cosmos DB: {endpoint}")
    print(f"📦 Database: {database_name}\n")
    
    # Use key-based authentication
    client = CosmosClient(endpoint, key)
    
    try:
        # Get or create database
        print(f"📊 Getting database '{database_name}'...")
        database = client.get_database_client(database_name)
        
        # Define all containers with their partition keys
        containers = [
            {
                "id": "parcels",
                "partition_key": "/store_location",
                "description": "Parcel records"
            },
            {
                "id": "TrackingEvents",
                "partition_key": "/barcode",
                "description": "Tracking event history"
            },
            {
                "id": "DeliveryAttempts",
                "partition_key": "/barcode",
                "description": "Delivery attempt records"
            },
            {
                "id": "feedback",
                "partition_key": "/tracking_number",
                "description": "Customer feedback"
            },
            {
                "id": "company_info",
                "partition_key": "/info_type",
                "description": "Company configuration"
            },
            {
                "id": "suspicious_messages",
                "partition_key": "/report_date",
                "description": "Fraud detection logs"
            },
            {
                "id": "address_history",
                "partition_key": "/address_normalized",
                "description": "Address history for smart routing"
            },
            {
                "id": "users",
                "partition_key": "/username",
                "description": "User accounts"
            },
            {
                "id": "Manifests",
                "partition_key": "/manifest_id",
                "description": "Driver delivery manifests"
            },
            {
                "id": "address_notes",
                "partition_key": "/address_normalized",
                "description": "Delivery address notes"
            },
        ]
        
        print(f"Creating {len(containers)} containers...\n")
        
        success_count = 0
        for container_spec in containers:
            try:
                container = await database.create_container_if_not_exists(
                    id=container_spec["id"],
                    partition_key=PartitionKey(path=container_spec["partition_key"]),
                    indexing_policy={
                        "indexingMode": "consistent",
                        "automatic": True,
                        "includedPaths": [{"path": "/*"}]
                    }
                )
                print(f"  ✅ {container_spec['id']:25} (PK: {container_spec['partition_key']:25}) - {container_spec['description']}")
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ {container_spec['id']:25} - Error: {str(e)[:80]}")
        
        print(f"\n{'='*80}")
        print(f"✅ Successfully initialized {success_count}/{len(containers)} containers")
        print(f"{'='*80}\n")
        
        # Test a simple query to verify permissions
        print("🧪 Testing permissions with sample query...")
        parcels_container = database.get_container_client("parcels")
        query = "SELECT TOP 1 * FROM c"
        items = []
        async for item in parcels_container.query_items(query=query):
            items.append(item)
        print(f"   ✅ Query successful (found {len(items)} items)\n")
        
        print("🎉 Initialization complete! You can now run data generation scripts.\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        print("💡 Make sure you have granted RBAC permissions:")
        print("   az cosmosdb sql role assignment create \\")
        print("      --account-name zava-dev-cosmos-77cd5n \\")
        print("      --resource-group RG-Zava-Backend-dev \\")
        print("      --scope / \\")
        print("      --principal-id $(az ad signed-in-user show --query id -o tsv) \\")
        print("      --role-definition-id 00000000-0000-0000-0000-000000000002")
        print("\n⏳ Wait 2-3 minutes after granting permissions for RBAC to propagate.\n")
        raise
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(initialize_containers())
