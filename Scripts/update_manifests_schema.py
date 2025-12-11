"""
Update existing manifests to include optimized and traffic_considered flags
"""
import asyncio
import os
from dotenv import load_dotenv
from parcel_tracking_db import ParcelTrackingDB

load_dotenv()

async def update_existing_manifests():
    """Add optimized and traffic_considered flags to existing manifests"""
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        container = db.database.get_container_client("driver_manifests")
        
        # Get all manifests
        query = "SELECT * FROM c"
        
        updated_count = 0
        manifests_to_update = []
        
        async for manifest in container.query_items(query=query):
            manifests_to_update.append(manifest)
        
        for manifest in manifests_to_update:
            # Check if manifest needs updating
            if 'optimized' not in manifest:
                manifest['optimized'] = True  # Assume existing optimized routes are real
                manifest['traffic_considered'] = True
                
                await container.replace_item(item=manifest['id'], body=manifest)
                print(f"✅ Updated manifest: {manifest['id']}")
                updated_count += 1
            else:
                print(f"⏭️  Skipped manifest (already has optimized flag): {manifest['id']}")
        
        print(f"\n{'='*60}")
        print(f"✅ Updated {updated_count} manifests")
        print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(update_existing_manifests())
