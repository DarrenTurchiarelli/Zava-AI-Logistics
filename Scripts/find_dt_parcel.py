"""
Find parcel with tracking number or check manifest items
"""

import asyncio
from parcel_tracking_db import ParcelTrackingDB


async def find_parcel():
    """Search for DT202512170037 in manifests and parcels"""
    
    print("="*70)
    print("Searching for DT202512170037")
    print("="*70)
    
    async with ParcelTrackingDB() as db:
        # Search in parcels by different fields
        parcels_container = db.database.get_container_client("parcels")
        
        # Try tracking_number
        print("\n1. Searching by tracking_number...")
        query = "SELECT c.id, c.tracking_number, c.barcode, c.recipient, c.status FROM c WHERE c.tracking_number = @search"
        params = [{"name": "@search", "value": "DT202512170037"}]
        items = []
        async for item in parcels_container.query_items(query=query, parameters=params):
            items.append(item)
        
        if items:
            print(f"   ✅ Found {len(items)} parcel(s) by tracking_number")
            for p in items:
                print(f"      ID: {p.get('id')}")
                print(f"      Tracking: {p.get('tracking_number')}")
                print(f"      Barcode: {p.get('barcode')}")
                print(f"      Status: {p.get('status')}")
        else:
            print("   ❌ No parcels found by tracking_number")
        
        # Try barcode
        print("\n2. Searching by barcode...")
        query2 = "SELECT c.id, c.tracking_number, c.barcode, c.recipient, c.status FROM c WHERE c.barcode = @search"
        items2 = []
        async for item in parcels_container.query_items(query=query2, parameters=params):
            items2.append(item)
        
        if items2:
            print(f"   ✅ Found {len(items2)} parcel(s) by barcode")
            for p in items2:
                print(f"      ID: {p.get('id')}")
                print(f"      Tracking: {p.get('tracking_number')}")
                print(f"      Barcode: {p.get('barcode')}")
                print(f"      Status: {p.get('status')}")
        else:
            print("   ❌ No parcels found by barcode")
        
        # Search manifests
        print("\n3. Searching in manifests...")
        manifests_container = db.database.get_container_client("manifests")
        query3 = "SELECT * FROM c"
        async for manifest in manifests_container.query_items(query=query3):
            for item in manifest.get('items', []):
                if 'DT202512170037' in str(item):
                    print(f"   ✅ Found in manifest: {manifest.get('manifest_id')}")
                    print(f"      Item: {item}")
                    break


if __name__ == "__main__":
    asyncio.run(find_parcel())
