"""
Delete duplicate manifests for today's date, keeping only the newest per driver
"""
import asyncio
import sys
import os
from collections import defaultdict
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parcel_tracking_db import ParcelTrackingDB

async def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n📅 Deleting duplicate manifests for date: {today}\n")
    
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        container = db.database.get_container_client("driver_manifests")
        
        # Query for all active manifests today
        query = "SELECT * FROM c WHERE c.status = 'active' AND c.manifest_date = @today"
        params = [{"name": "@today", "value": today}]
        
        manifests = []
        async for item in container.query_items(query=query, parameters=params):
            manifests.append(item)
        
        print(f"Total active manifests today: {len(manifests)}")
        
        # Group by driver_id
        by_driver = defaultdict(list)
        for m in manifests:
            by_driver[m['driver_id']].append(m)
        
        # Find duplicates
        to_delete = []
        for driver_id, driver_manifests in sorted(by_driver.items()):
            if len(driver_manifests) > 1:
                # Sort by created_timestamp DESC (newest first)
                driver_manifests.sort(key=lambda x: x.get('created_timestamp', ''), reverse=True)
                
                # Keep the first (newest), mark the rest for deletion
                keep = driver_manifests[0]
                delete = driver_manifests[1:]
                
                print(f"\n❌ {driver_id}: {len(driver_manifests)} manifests found")
                print(f"   ✅ KEEPING: {keep['id']} (Created: {keep.get('created_timestamp', 'N/A')})")
                print(f"   🗑️  DELETING {len(delete)} older manifests:")
                for m in delete:
                    print(f"      - {m['id']} (Created: {m.get('created_timestamp', 'N/A')})")
                    to_delete.append(m)
        
        if not to_delete:
            print("\n✅ No duplicate manifests found!")
            return
        
        print(f"\n🔥 Ready to delete {len(to_delete)} duplicate manifests")
        print("⏳ Deleting...")
        
        deleted_count = 0
        failed_count = 0
        
        for manifest in to_delete:
            try:
                await container.delete_item(
                    item=manifest['id'],
                    partition_key=manifest['driver_id']
                )
                deleted_count += 1
                print(f"✅ Deleted: {manifest['id']}")
            except Exception as e:
                failed_count += 1
                print(f"❌ Error deleting {manifest['id']}: {e}")
        
        print("\n" + "=" * 80)
        print(f"✅ COMPLETED:")
        print(f"   Deleted: {deleted_count} manifests")
        print(f"   Failed: {failed_count} manifests")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
