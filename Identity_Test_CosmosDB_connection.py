#!/usr/bin/env python3
"""
Quick test for Cosmos DB Azure AD authentication
"""

import asyncio
import os
from dotenv import load_dotenv
from cosmosdb_tools import get_db_manager

async def test_connection():
    """Test Cosmos DB connection with Azure AD auth"""
    load_dotenv()
    
    print("Testing Azure Cosmos DB connection...")
    print(f"Endpoint: {os.getenv('COSMOS_DB_ENDPOINT')}")
    print(f"Database: {os.getenv('COSMOS_DB_DATABASE_NAME', 'logistics_tracking_db')}")
    
    try:
        # Test getting the database manager
        db = await get_db_manager()
        print("✅ Successfully connected to Cosmos DB!")
        
        # Test getting container
        container = db.database.get_container_client(db.parcels_container)
        print("✅ Successfully got parcels container!")
        
        # Test querying (this will show if auth really works)
        items = []
        try:
            async for item in container.query_items(
                query="SELECT * FROM c OFFSET 0 LIMIT 5"
            ):
                items.append(item)
            print(f"✅ Successfully queried database - found {len(items)} parcels")
            
        except Exception as query_error:
            print(f"⚠️  Query failed: {query_error}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())