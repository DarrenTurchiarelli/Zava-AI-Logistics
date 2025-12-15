"""Reset route optimization for first 3 drivers"""
import asyncio
from parcel_tracking_db import ParcelTrackingDB

async def reset_drivers():
    async with ParcelTrackingDB() as db:
        container = db.database.get_container_client('driver_manifests')
        
        for driver_id in ['driver-001', 'driver-002', 'driver-003']:
            query = 'SELECT * FROM c WHERE c.driver_id = @driver_id'
            parameters = [{'name': '@driver_id', 'value': driver_id}]
            
            async for manifest in container.query_items(query=query, parameters=parameters):
                manifest['route_optimized'] = False
                manifest['optimized_route'] = None
                manifest['optimization_progress'] = 0
                manifest['optimization_step'] = None
                await container.replace_item(item=manifest['id'], body=manifest)
                print(f'✅ Reset optimization for {manifest["driver_name"]} ({manifest["id"]})')
                break

if __name__ == '__main__':
    asyncio.run(reset_drivers())
    print('\n✅ Done! Log in as driver-001, driver-002, or driver-003 to see route optimization!')
