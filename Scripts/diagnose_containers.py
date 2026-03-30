"""
Diagnose Cosmos DB container setup
Checks which containers exist and which are missing
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import asyncio
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def diagnose_containers():
    """Check which containers exist in the database"""
    print("=" * 80)
    print("Cosmos DB Container Diagnostic")
    print("=" * 80)
    
    # Get connection details
    connection_string = os.getenv("COSMOS_CONNECTION_STRING")
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "logisticstracking")
    use_managed_identity = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"
    
    print(f"Database: {database_name}")
    print(f"Endpoint: {endpoint}")
    print(f"Auth method: {'Managed Identity' if use_managed_identity else 'Connection String/Azure AD'}\n")
    
    # Initialize client
    client = None
    credential = None
    
    try:
        if connection_string:
            # Parse connection string
            parts = connection_string.split(";")
            endpoint = parts[0].replace("AccountEndpoint=", "")
            key = parts[1].replace("AccountKey=", "")
            print("Using connection string authentication\n")
            client = CosmosClient(endpoint, key)
        elif use_managed_identity:
            print("Using managed identity authentication\n")
            credential = ManagedIdentityCredential()
            client = CosmosClient(endpoint, credential)
        elif endpoint:
            print("Using Azure AD (DefaultAzureCredential) authentication\n")
            credential = DefaultAzureCredential()
            client = CosmosClient(endpoint, credential)
        else:
            print("❌ ERROR: No Cosmos DB connection details found")
            print("   Set COSMOS_CONNECTION_STRING or COSMOS_DB_ENDPOINT")
            return False
        
        # Get database
        try:
            database = client.get_database_client(database_name)
            # Test database access
            await database.read()
            print(f"✓ Database '{database_name}' exists and is accessible\n")
        except Exception as e:
            print(f"❌ ERROR: Cannot access database '{database_name}'")
            print(f"   {str(e)}\n")
            return False
        
        # Expected containers
        expected_containers = [
            ("parcels", "/store_location", "Parcel records"),
            ("TrackingEvents", "/barcode", "Tracking event history"),
            ("DeliveryAttempts", "/barcode", "Delivery attempt records"),
            ("feedback", "/tracking_number", "Customer feedback"),
            ("company_info", "/info_type", "Company configuration"),
            ("suspicious_messages", "/report_date", "Fraud detection logs"),
            ("address_history", "/address_normalized", "Address history"),
            ("users", "/username", "User accounts"),
            ("Manifests", "/manifest_id", "Driver manifests"),
            ("address_notes", "/address_normalized", "Delivery notes"),
        ]
        
        # Check each container
        print("Checking containers...")
        print("-" * 80)
        
        existing_count = 0
        missing_containers = []
        
        for container_id, partition_key, description in expected_containers:
            try:
                container = database.get_container_client(container_id)
                await container.read()
                print(f"  ✓ {container_id:25} (PK: {partition_key:25}) - {description}")
                existing_count += 1
            except Exception:
                print(f"  ✗ {container_id:25} (PK: {partition_key:25}) - MISSING")
                missing_containers.append((container_id, partition_key, description))
        
        print("-" * 80)
        print(f"Status: {existing_count}/{len(expected_containers)} containers exist\n")
        
        if missing_containers:
            print("=" * 80)
            print("MISSING CONTAINERS")
            print("=" * 80)
            for container_id, partition_key, description in missing_containers:
                print(f"  • {container_id:25} (PK: {partition_key})")
            print("\n💡 Run this command to create missing containers:")
            print("   python Scripts/initialize_all_containers.py")
            print("=" * 80)
            return False
        else:
            print("=" * 80)
            print("✅ All containers exist and are accessible!")
            print("=" * 80)
            return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 Troubleshooting steps:")
        print("   1. Check COSMOS_DB_ENDPOINT is set correctly")
        print("   2. Verify RBAC permissions (Cosmos DB Built-in Data Contributor)")
        print("   3. For local dev: Run 'az login' and try again")
        print("   4. For Azure: Verify managed identity is enabled")
        return False
    finally:
        if client:
            await client.close()
        if credential:
            await credential.close()


if __name__ == "__main__":
    success = asyncio.run(diagnose_containers())
    sys.exit(0 if success else 1)
