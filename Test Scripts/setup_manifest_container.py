#!/usr/bin/env python3
"""
Setup script to create the driver_manifests container in Cosmos DB
Run this once to initialize the manifest system
"""

import asyncio
import os
from azure.cosmos import exceptions, PartitionKey
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

async def create_manifest_container():
    """Create the driver_manifests container if it doesn't exist"""
    
    # Get connection details from environment
    endpoint = os.getenv('COSMOS_DB_ENDPOINT')
    database_name = os.getenv('COSMOS_DB_DATABASE_NAME', 'agent_workflow_db')
    
    if not endpoint:
        print("❌ COSMOS_DB_ENDPOINT not found in .env")
        return False
    
    print(f"🔧 Connecting to Cosmos DB...")
    print(f"   Endpoint: {endpoint}")
    print(f"   Database: {database_name}")
    print(f"   Auth: Azure AD (DefaultAzureCredential)")
    
    # Use Azure AD authentication
    credential = DefaultAzureCredential()
    
    async with CosmosClient(endpoint, credential=credential) as client:
        try:
            # Get database
            database = client.get_database_client(database_name)
            
            # Check if container exists
            container_name = "driver_manifests"
            
            try:
                container = database.get_container_client(container_name)
                # Try to read container properties to verify it exists
                await container.read()
                print(f"✅ Container '{container_name}' already exists")
                return True
                
            except exceptions.CosmosResourceNotFoundError:
                print(f"📦 Creating container '{container_name}'...")
                
                # Create container with partition key on driver_id
                # Don't specify throughput for serverless accounts
                container = await database.create_container(
                    id=container_name,
                    partition_key=PartitionKey(path="/driver_id")
                )
                
                print(f"✅ Container '{container_name}' created successfully!")
                print(f"   Partition Key: /driver_id")
                print(f"   Mode: Serverless (no throughput configuration)")
                
                # Create sample indexes (optional but recommended)
                print(f"📑 Configuring indexing policy...")
                
                return True
                
        except exceptions.CosmosResourceNotFoundError:
            print(f"❌ Database '{database_name}' not found!")
            print(f"   Please ensure the database exists in Cosmos DB")
            return False
            
        except Exception as e:
            print(f"❌ Error creating container: {e}")
            return False

async def verify_setup():
    """Verify the container is accessible"""
    
    endpoint = os.getenv('COSMOS_DB_ENDPOINT')
    database_name = os.getenv('COSMOS_DB_DATABASE_NAME', 'agent_workflow_db')
    
    credential = DefaultAzureCredential()
    
    async with CosmosClient(endpoint, credential=credential) as client:
        database = client.get_database_client(database_name)
        container = database.get_container_client("driver_manifests")
        
        # Just verify we can read the container properties
        properties = await container.read()
        
        print(f"✅ Container is accessible and ready to use")
        print(f"   Container ID: {properties.get('id')}")
        print(f"   Partition Key: {properties.get('partitionKey', {}).get('paths', ['N/A'])[0]}")
        
        return True

async def main():
    """Main setup function"""
    print("=" * 60)
    print("Driver Manifest Container Setup")
    print("=" * 60)
    print()
    
    # Create container
    success = await create_manifest_container()
    
    if success:
        print()
        print("🔍 Verifying setup...")
        await verify_setup()
        
        print()
        print("=" * 60)
        print("✅ Setup Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Restart your Flask application")
        print("2. Navigate to /admin/manifests to create a manifest")
        print("3. Navigate to /driver/manifest to view driver manifests")
        print()
    else:
        print()
        print("=" * 60)
        print("❌ Setup Failed")
        print("=" * 60)
        print()
        print("Please check the error messages above and try again")
        print()

if __name__ == "__main__":
    asyncio.run(main())
