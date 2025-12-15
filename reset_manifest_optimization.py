"""Reset route optimization for a driver's manifest"""
import asyncio
from parcel_tracking_db import ParcelTrackingDB

async def reset_optimization(driver_id='driver-001'):
    async with ParcelTrackingDB() as db:
        container = db.database.get_container_client('driver_manifests')
        query = 'SELECT * FROM c WHERE c.driver_id = @driver_id'
        parameters = [{'name': '@driver_id', 'value': driver_id}]
        
        async for manifest in container.query_items(query=query, parameters=parameters):
            manifest['route_optimized'] = False
            manifest['optimized_route'] = None
            await container.replace_item(item=manifest['id'], body=manifest)
            print(f'✅ Reset optimization for manifest {manifest["id"]}')
            break

if __name__ == '__main__':
    asyncio.run(reset_optimization())
    print('✅ Done! Refresh the driver manifest page to see re-optimization with address grouping.')
