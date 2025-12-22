import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parcel_tracking_db import ParcelTrackingDB

async def check_formats():
    async with ParcelTrackingDB() as db:
        container = db.database.get_container_client('driver_manifests')
        query = 'SELECT c.driver_id FROM c WHERE c.status = "active" AND c.manifest_date = "2025-12-22"'
        
        hyphenated = []
        non_hyphenated = []
        
        async for item in container.query_items(query=query):
            driver_id = item['driver_id']
            if '-' in driver_id and driver_id.startswith('driver'):
                hyphenated.append(driver_id)
            elif driver_id.startswith('driver') and not '-' in driver_id:
                if len(driver_id) > 6 and driver_id[6:9].replace('0','').isdigit():
                    non_hyphenated.append(driver_id)
        
        print('\n✅ Hyphenated (MATCHES login format - driver001/driver123):')
        for d in sorted(hyphenated):
            print(f'   {d}')
        
        print(f'\n⚠️  Non-hyphenated (NO matching login account):')
        for d in sorted(non_hyphenated):
            print(f'   {d}')
        
        print(f'\nSummary:')
        print(f'   Hyphenated: {len(hyphenated)} (can login)')
        print(f'   Non-hyphenated: {len(non_hyphenated)} (CANNOT login)')

asyncio.run(check_formats())
