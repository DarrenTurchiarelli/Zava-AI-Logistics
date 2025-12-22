"""Delete duplicate manifests for TODAY only, keeping most recent"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parcel_tracking_db import ParcelTrackingDB

async def delete_todays_duplicates():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n📅 Deleting duplicate manifests for: {today}\n")
    
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
        
        print(f"Total active manifests today: {len(manifests)}")
        
        # Group by driver_id
        by_driver = defaultdict(list)
        for m in manifests:
            by_driver[m['driver_id']].append(m)
        
        # Find duplicates to delete
        to_delete = []
        for driver_id, driver_manifests in by_driver.items():
            if len(driver_manifests) > 1:
                # Sort by created_timestamp descending (newest first)
                driver_manifests.sort(key=lambda x: x.get('created_timestamp', ''), reverse=True)
                
                # Keep first (newest), delete rest
                keep = driver_manifests[0]
                delete = driver_manifests[1:]
                
                print(f"\n❌ {driver_id}: {len(driver_manifests)} manifests")
                print(f"   KEEP: {keep['id']}")
                print(f"   DELETE: {len(delete)} older manifests")
                
                to_delete.extend(delete)
        
        if not to_delete:
            print("\n✅ No duplicates found!")
            return
        
        print(f"\n{'='*80}")
        print(f"⚠️  WILL DELETE: {len(to_delete)} duplicate manifests")
        print(f"⚠️  WILL KEEP: {len(by_driver)} unique manifests (one per driver)")
        print(f"{'='*80}\n")
        
        # Delete without confirmation since this is a script
        deleted = 0
        for manifest in to_delete:
            try:
                await container.delete_item(
                    item=manifest['id'],
                    partition_key=manifest['id']
                )
                deleted += 1
                print(f"✅ Deleted: {manifest['id']}")
            except Exception as e:
                print(f"❌ Error deleting {manifest['id']}: {e}")
        
        print(f"\n{'='*80}")
        print(f"✅ COMPLETED: Deleted {deleted} duplicate manifests")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(delete_todays_duplicates())
