"""Reset driver-002 manifest optimization flag"""
import asyncio
from parcel_tracking_db import ParcelTrackingDB

async def reset_driver002():
    """Reset optimization for driver-002 manifest"""
    
    async with ParcelTrackingDB() as db:
        manifest_container = db.database.get_container_client('driver_manifests')
        
        # Find driver-002 manifest
        query = 'SELECT * FROM c WHERE c.driver_id = "driver-002"'
        
        async for manifest in manifest_container.query_items(query=query):
            # Reset optimization flags
            manifest['route_optimized'] = False
            manifest['optimized_route'] = None
            manifest['optimization_progress'] = 0
            manifest['optimization_step'] = 'Not started'
            manifest['all_routes'] = None
            manifest['route_options'] = None
            manifest['estimated_duration_minutes'] = None
            manifest['estimated_distance_km'] = None
            
            await manifest_container.replace_item(item=manifest['id'], body=manifest)
            print(f"✅ Reset optimization for {manifest['driver_name']} ({manifest['id']})")
            print(f"   Total items: {manifest['total_items']}")

if __name__ == '__main__':
    asyncio.run(reset_driver002())
    print("\n✅ Done! Log in as driver002 to trigger route optimization!")
