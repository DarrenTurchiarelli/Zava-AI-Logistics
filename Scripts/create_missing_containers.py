"""
Create missing Cosmos DB containers (simple version without emojis)
"""
import asyncio
import os
from dotenv import load_dotenv
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey

load_dotenv()

async def create_missing_containers():
    """Create containers that are missing"""
    
    # Get connection string
    connection_string = os.getenv("COSMOS_CONNECTION_STRING")
    if not connection_string:
        print("ERROR: COSMOS_CONNECTION_STRING not found")
        return
    
    # Parse endpoint and key
    parts = connection_string.split(";")
    endpoint = parts[0].replace("AccountEndpoint=", "")
    key = parts[1].replace("AccountKey=", "")
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "logisticstracking")
    
    print(f"Connecting to: {endpoint}")
    print(f"Database: {database_name}\n")
    
    # Use key-based authentication
    client = CosmosClient(endpoint, key)
    
    try:
        # Get database
        database = await client.create_database_if_not_exists(id=database_name)
        print(f"Database '{database_name}' ready\n")
        
        # Define missing containers
        containers = [
            ("TrackingEvents", "/barcode"),
            ("DeliveryAttempts", "/barcode"),
            ("feedback", "/tracking_number"),
            ("company_info", "/info_type"),
            ("suspicious_messages", "/report_date"),
            ("address_history", "/address_normalized"),
            ("Manifests", "/manifest_id"),
        ]
        
        success_count = 0
        for container_id, partition_key in containers:
            try:
                await database.create_container_if_not_exists(
                    id=container_id,
                    partition_key=PartitionKey(path=partition_key),
                )
                print(f"[OK] {container_id} (PK: {partition_key})")
                success_count += 1
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"[ERROR] {container_id}: {error_msg}")
        
        print(f"\nCreated successfully: {success_count}/{len(containers)} containers")
        
    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(create_missing_containers())
