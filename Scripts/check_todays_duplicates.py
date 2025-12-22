"""Check for duplicate manifests TODAY specifically"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parcel_tracking_db import ParcelTrackingDB

async def check_todays_duplicates():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n📅 Checking manifests for date: {today}\n")
    
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        container = db.database.get_container_client("driver_manifests")
        
        # Query for today's active manifests
        query = "SELECT * FROM c WHERE c.status = 'active' AND c.manifest_date = @today"
        params = [{"name": "@today", "value": today}]
        
        manifests = []
        async for manifest in container.query_items(query=query, parameters=params):
            manifests.append(manifest)
        
        print(f"Total active manifests today: {len(manifests)}\n")
        
        # Group by driver_id
        by_driver = defaultdict(list)
        for m in manifests:
            by_driver[m['driver_id']].append(m)
        
        # Show duplicates
        has_duplicates = False
        for driver_id, driver_manifests in sorted(by_driver.items()):
            if len(driver_manifests) > 1:
                has_duplicates = True
                print(f"❌ DUPLICATE: {driver_id} has {len(driver_manifests)} manifests:")
                for m in sorted(driver_manifests, key=lambda x: x.get('created_timestamp', '')):
                    print(f"   - {m['id']}")
                    print(f"     Created: {m.get('created_timestamp', 'N/A')}")
                    print(f"     Parcels: {len(m.get('parcel_barcodes', []))}")
                print()
            else:
                m = driver_manifests[0]
                print(f"✅ {driver_id}: 1 manifest ({m['id']}) - {len(m.get('parcel_barcodes', []))} parcels")
        
        if not has_duplicates:
            print("\n✅ No duplicates found!")
        else:
            print("\n⚠️  Duplicates detected - ready to delete older ones")

if __name__ == "__main__":
    asyncio.run(check_todays_duplicates())
