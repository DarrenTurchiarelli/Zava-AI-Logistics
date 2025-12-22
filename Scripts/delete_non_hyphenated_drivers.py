import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parcel_tracking_db import ParcelTrackingDB

async def delete_non_hyphenated():
    async with ParcelTrackingDB() as db:
        container = db.database.get_container_client('driver_manifests')
        query = 'SELECT * FROM c WHERE c.status = "active" AND c.manifest_date = "2025-12-22"'
        
        to_delete = []
        
        async for item in container.query_items(query=query):
            driver_id = item['driver_id']
            # Find non-hyphenated driver IDs (driver001, driver002, etc.)
            if driver_id.startswith('driver') and '-' not in driver_id:
                if len(driver_id) > 6 and driver_id[6:9].replace('0','').isdigit():
                    to_delete.append(item)
        
        print(f'\n🗑️  Deleting {len(to_delete)} non-hyphenated manifests (no matching login accounts):\n')
        
        deleted = 0
        for manifest in to_delete:
            try:
                await container.delete_item(
                    item=manifest['id'],
                    partition_key=manifest['driver_id']
                )
                print(f'✅ Deleted: {manifest["id"]} (driver_id: {manifest["driver_id"]})')
                deleted += 1
            except Exception as e:
                print(f'❌ Error deleting {manifest["id"]}: {e}')
        
        print(f'\n✅ Complete! Deleted {deleted} manifests')
        print(f'   Remaining manifests will all have matching login accounts')

asyncio.run(delete_non_hyphenated())
