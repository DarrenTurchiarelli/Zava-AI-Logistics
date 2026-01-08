"""Delete ALL demo data (parcels and manifests)"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parcel_tracking_db import ParcelTrackingDB

async def delete_all_demo_data():
    """Delete all parcels and manifests"""
    async with ParcelTrackingDB() as db:
        await db.connect()
        
        # Delete all manifests
        print("🗑️  Deleting all manifests...")
        manifests_container = db.database.get_container_client("driver_manifests")
        query = "SELECT c.id, c.driver_id FROM c"
        deleted_manifests = 0
        async for manifest in manifests_container.query_items(query=query):
            await manifests_container.delete_item(item=manifest['id'], partition_key=manifest['driver_id'])
            deleted_manifests += 1
            if deleted_manifests % 10 == 0:
                print(f"   Deleted {deleted_manifests} manifests...")
        print(f"✅ Deleted {deleted_manifests} manifests")
        
        # Delete all parcels
        print("\n📦 Deleting all parcels...")
        parcels_container = db.database.get_container_client(db.parcels_container)
        query = "SELECT c.id, c.barcode FROM c"
        deleted_parcels = 0
        async for parcel in parcels_container.query_items(query=query):
            try:
                await parcels_container.delete_item(item=parcel['id'], partition_key=parcel['barcode'])
                deleted_parcels += 1
                if deleted_parcels % 100 == 0:
                    print(f"   Deleted {deleted_parcels} parcels...")
            except Exception as e:
                if "NotFound" not in str(e):
                    print(f"   Error deleting parcel {parcel['barcode']}: {e}")
        print(f"✅ Deleted {deleted_parcels} parcels")
        
        print(f"\n🎉 All demo data deleted! Ready to regenerate.")

if __name__ == '__main__':
    asyncio.run(delete_all_demo_data())
