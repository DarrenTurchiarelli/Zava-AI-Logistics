#!/usr/bin/env python3
"""
Setup Address Notes Container in Cosmos DB

This script creates the address_notes container for storing
driver notes about delivery addresses.
"""

import asyncio
import os
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions
from azure.identity.aio import DefaultAzureCredential, AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

async def setup_address_notes_container():
    """Create the address_notes container if it doesn't exist"""
    
    # Get Cosmos DB connection details (using same variable names as main app)
    endpoint = os.getenv('COSMOS_DB_ENDPOINT')
    database_name = os.getenv('COSMOS_DB_DATABASE_NAME', 'agent_workflow_db')
    
    if not endpoint:
        print("❌ COSMOS_DB_ENDPOINT not configured")
        return
    
    print(f"🔧 Connecting to Cosmos DB: {database_name}")
    print(f"   Endpoint: {endpoint}")
    
    # Use Azure AD authentication (same as main app)
    try:
        credential = AzureCliCredential()
        print("   Using Azure CLI credentials")
    except Exception as e:
        print(f"   ⚠️ Azure CLI not available, trying DefaultAzureCredential")
        credential = DefaultAzureCredential()
    
    async with CosmosClient(endpoint, credential) as client:
        # Get database
        database = client.get_database_client(database_name)
        
        # Create address_notes container
        container_name = "address_notes"
        
        try:
            # Check if container already exists
            container = database.get_container_client(container_name)
            await container.read()
            print(f"✅ Container '{container_name}' already exists")
        except exceptions.CosmosResourceNotFoundError:
            # Create the container
            print(f"📦 Creating container '{container_name}'...")
            await database.create_container(
                id=container_name,
                partition_key=PartitionKey(path="/normalized_address")
                # No throughput for serverless accounts
            )
            print(f"✅ Created container '{container_name}' successfully")
        
        # Verify container setup
        properties = await database.get_container_client(container_name).read()
        print(f"\n📊 Container Details:")
        print(f"   Name: {properties['id']}")
        print(f"   Partition Key: {properties['partitionKey']['paths'][0]}")
        
        print("\n✅ Address notes container setup complete!")
        print("\n💡 Drivers can now add notes about delivery addresses.")
        print("   Notes will be displayed on future deliveries to the same address.")

if __name__ == "__main__":
    asyncio.run(setup_address_notes_container())
