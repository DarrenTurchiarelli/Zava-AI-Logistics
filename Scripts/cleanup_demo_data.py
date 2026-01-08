"""Delete all demo parcels and manifests to prepare for fresh regeneration"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parcel_tracking_db import ParcelTrackingDB

async def cleanup_demo_data():
    """Delete all parcels and manifests"""
    async with ParcelTrackingDB() as db:
        await db.connect()
        
        # Delete all parcels
        print("🗑️  Deleting all parcels...")
        parcels_container = db.database.get_container_client(db.parcels_container)
        
        query = "SELECT c.id, c.barcode FROM c"
        parcels_deleted = 0
        async for parcel in parcels_container.query_items(query=query):
            try:
                await parcels_container.delete_item(item=parcel['id'], partition_key=parcel['barcode'])
                parcels_deleted += 1
                if parcels_deleted % 100 == 0:
                    print(f"   Deleted {parcels_deleted} parcels...")
            except Exception as e:
                if "NotFound" not in str(e):
                    print(f"   ⚠️  Error deleting parcel {parcel['barcode']}: {e}")
        
        print(f"✅ Deleted {parcels_deleted} parcels")
        
        # Delete all manifests
        print("\n🗑️  Deleting all driver manifests...")
        manifests_container = db.database.get_container_client(db.driver_manifests_container)
        
        query = "SELECT c.id, c.driver_id FROM c"
        manifests_deleted = 0
        async for manifest in manifests_container.query_items(query=query):
            try:
                await manifests_container.delete_item(item=manifest['id'], partition_key=manifest['driver_id'])
                manifests_deleted += 1
            except Exception as e:
                if "NotFound" not in str(e):
                    print(f"   ⚠️  Error deleting manifest {manifest['id']}: {e}")
        
        print(f"✅ Deleted {manifests_deleted} manifests")
        
        print(f"\n✨ Cleanup complete! Ready to regenerate demo data.")
        print(f"   Run: python utils/generators/generate_demo_manifests.py")

if __name__ == '__main__':
    asyncio.run(cleanup_demo_data())
