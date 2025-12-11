#!/usr/bin/env python3
"""
Quick test for Cosmos DB Azure AD authentication
"""

import asyncio
import os
from dotenv import load_dotenv
from parcel_tracking_db import ParcelTrackingDB

async def test_connection():
    """Test Cosmos DB connection with Azure AD auth"""
    load_dotenv()
    
    print("Testing Azure Cosmos DB connection...")
    print(f"Endpoint: {os.getenv('COSMOS_DB_ENDPOINT')}")
    print(f"Database: {os.getenv('COSMOS_DB_DATABASE_NAME', 'logistics_tracking_db')}")
    
    try:
        # Test getting the database manager
        async with ParcelTrackingDB() as db:
            print("✅ Successfully connected to Cosmos DB!")
            
            # Test basic functionality
            parcels = await db.get_all_parcels()
            print(f"✅ Successfully queried database - found {len(parcels)} parcels")
            
            # Test database health
            print("✅ Database connection and authentication working properly!")
            
            # Show some basic stats if we have data
            if parcels:
                print(f"📊 Database stats:")
                print(f"   - Total parcels: {len(parcels)}")
                statuses = {}
                for parcel in parcels:
                    status = parcel.get('current_status', 'unknown')
                    statuses[status] = statuses.get(status, 0) + 1
                for status, count in statuses.items():
                    print(f"   - {status.title()}: {count}")
            else:
                print("📭 No parcels in database yet")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())