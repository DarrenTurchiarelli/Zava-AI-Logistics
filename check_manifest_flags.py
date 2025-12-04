"""
Check manifest optimized flags
"""
import asyncio
from parcel_tracking_db import ParcelTrackingDB

async def check_manifests():
    """Check optimized flags in manifests"""
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        container = db.database.get_container_client("driver_manifests")
        query = "SELECT c.id, c.optimized, c.traffic_considered, c.route_optimized FROM c"
        
        print("\n" + "="*80)
        print("MANIFEST OPTIMIZATION STATUS")
        print("="*80)
        
        async for manifest in container.query_items(query=query):
            print(f"\nManifest ID: {manifest.get('id')}")
            print(f"  route_optimized: {manifest.get('route_optimized')}")
            print(f"  optimized: {manifest.get('optimized')}")
            print(f"  traffic_considered: {manifest.get('traffic_considered')}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(check_manifests())
