"""
Initialize all Cosmos DB containers in one operation
This script creates ALL 10 containers required by the Zava Logistics system
Run this during deployment to set up the database structure
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import asyncio
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.identity.aio import DefaultAzureCredential


async def initialize_all_containers():
    """Create all database containers in one operation"""
    print("=" * 80)
    print("Initializing Cosmos DB Containers")
    print("=" * 80)
    
    # Get connection details
    connection_string = os.getenv("COSMOS_CONNECTION_STRING")
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "logisticstracking")
    
    # Use connection string if available (deployment), otherwise Azure AD (local dev)
    if connection_string:
        # Parse connection string
        parts = connection_string.split(";")
        endpoint = parts[0].replace("AccountEndpoint=", "")
        key = parts[1].replace("AccountKey=", "")
        print(f"Using key-based authentication")
        client = CosmosClient(endpoint, key)
    elif endpoint:
        print(f"Using Azure AD authentication")
        credential = DefaultAzureCredential()
        client = CosmosClient(endpoint, credential)
    else:
        print("ERROR: No Cosmos DB connection details found")
        print("Set COSMOS_CONNECTION_STRING or COSMOS_DB_ENDPOINT")
        return False
    
    print(f"Database: {database_name}")
    print(f"Endpoint: {endpoint}\n")
    
    try:
        # Create or get database
        database = await client.create_database_if_not_exists(id=database_name)
        
        # Define all 10 containers with partition keys
        containers = [
            ("parcels", "/store_location", "Parcel records"),
            ("tracking_events", "/barcode", "Tracking event history"),
            ("delivery_attempts", "/barcode", "Delivery attempt records"),
            ("feedback", "/tracking_number", "Customer feedback"),
            ("company_info", "/info_type", "Company configuration"),
            ("suspicious_messages", "/report_date", "Fraud detection logs"),
            ("address_history", "/address_normalized", "Address history"),
            ("users", "/username", "User accounts"),
            ("Manifests", "/manifest_id", "Driver manifests"),
            ("address_notes", "/address_normalized", "Delivery notes"),
        ]
        
        print("Creating containers...\n")
        success_count = 0
        
        for container_id, partition_key, description in containers:
            try:
                await database.create_container_if_not_exists(
                    id=container_id,
                    partition_key=PartitionKey(path=partition_key),
                    indexing_policy={
                        "indexingMode": "consistent",
                        "automatic": True,
                        "includedPaths": [{"path": "/*"}]
                    }
                )
                print(f"  ✓ {container_id:25} (PK: {partition_key:25}) - {description}")
                success_count += 1
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"  ✗ {container_id:25} - {error_msg}")
        
        print(f"\n{'=' * 80}")
        print(f"SUCCESS: {success_count}/{len(containers)} containers initialized")
        print("=" * 80)
        
        return success_count == len(containers)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print("=" * 80)
        return False
    finally:
        await client.close()
        if connection_string and 'credential' in locals():
            await credential.close()


if __name__ == "__main__":
    success = asyncio.run(initialize_all_containers())
    sys.exit(0 if success else 1)
