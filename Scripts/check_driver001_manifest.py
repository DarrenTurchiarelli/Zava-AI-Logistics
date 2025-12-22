"""Check if driver-001 has a manifest"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parcel_tracking_db import ParcelTrackingDB

async def check_driver_manifest():
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        driver_id = "driver-001"
        
        print(f"Checking for manifest with driver_id: {driver_id}")
        print("=" * 70)
        
        manifest = await db.get_driver_manifest(driver_id)
        
        if manifest:
            print(f"✅ Found manifest!")
            print(f"   ID: {manifest.get('id')}")
            print(f"   Driver ID: {manifest.get('driver_id')}")
            print(f"   Driver Name: {manifest.get('driver_name')}")
            print(f"   Driver Location: {manifest.get('driver_location')}")
            print(f"   Driver State: {manifest.get('driver_state')}")
            print(f"   Total Items: {manifest.get('total_items')}")
            print(f"   Status: {manifest.get('status')}")
        else:
            print(f"❌ No manifest found for {driver_id}")
            print("\nSearching all active manifests...")
            
            container = db.database.get_container_client("driver_manifests")
            query = "SELECT * FROM c WHERE c.status = 'active' ORDER BY c.manifest_date DESC"
            
            manifests = []
            async for m in container.query_items(query=query):
                manifests.append(m)
            
            print(f"\nFound {len(manifests)} total active manifests")
            
            # Show first 10
            for m in manifests[:10]:
                print(f"   - {m.get('driver_id')}: {m.get('driver_name')} ({m.get('total_items')} items)")

if __name__ == "__main__":
    asyncio.run(check_driver_manifest())
