"""Check what data exists in the database"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parcel_tracking_db import ParcelTrackingDB

async def check_data():
    """Check current database state"""
    async with ParcelTrackingDB() as db:
        await db.connect()
        
        # Check parcels
        parcels_container = db.database.get_container_client(db.parcels_container)
        query = "SELECT c.barcode, c.recipient_address, c.destination_city, c.destination_state FROM c"
        count = 0
        print(f"\n📍 Sample parcels:")
        async for item in parcels_container.query_items(query=query, max_item_count=5):
            count += 1
            print(f"   {item['barcode']}: {item.get('recipient_address', 'N/A')}")
            print(f"      → City: {item.get('destination_city', 'N/A')}, State: {item.get('destination_state', 'N/A')}")
            if count >= 5:
                break
        
        # Check manifests
        manifests_container = db.database.get_container_client(db.manifests_container)
        query = "SELECT c.id, c.driver_id, c.driver_name, c.driver_location, c.total_items FROM c"
        print(f"\n🚚 Driver Manifests:")
        manifest_count = 0
        async for manifest in manifests_container.query_items(query=query, max_item_count=10):
            manifest_count += 1
            if manifest_count <= 5:
                print(f"   {manifest['driver_id']} ({manifest.get('driver_name', 'N/A')}): {manifest.get('total_items', 0)} parcels, Location: {manifest.get('driver_location', 'N/A')}")
        print(f"\n   Total manifests checked: {manifest_count}")
        
        # Check specific driver-001
        print(f"\n🔍 Checking driver-001 specifically:")
        manifest = await db.get_driver_manifest('driver-001')
        if manifest:
            print(f"   ✅ Manifest exists: {manifest['id']}")
            print(f"      Driver: {manifest['driver_name']}")
            print(f"      Location: {manifest.get('driver_location')}")
            print(f"      Total items: {manifest.get('total_items')}")
            if manifest.get('items'):
                print(f"      Sample item cities:")
                for item in manifest['items'][:3]:
                    print(f"         - {item.get('destination_city')}")
        else:
            print(f"   ❌ No manifest found for driver-001")

if __name__ == '__main__':
    asyncio.run(check_data())
