import asyncio
from parcel_tracking_db import ParcelTrackingDB

async def check():
    db = ParcelTrackingDB()
    await db.connect()
    
    # Check manifests
    print('\n=== Manifests Check ===')
    manifests = await db.get_all_active_manifests()
    print(f'Active manifests: {len(manifests)}')
    
    if manifests:
        print('\nSample manifests:')
        for m in manifests[:5]:
            manifest_id = m.get('manifest_id', 'NO_ID')
            driver = m.get('driver_user_id', 'NO_DRIVER')
            parcel_count = len(m.get('parcels', []))
            print(f'  - {manifest_id}: {driver} ({parcel_count} parcels)')
    
    # Check approvals
    print('\n=== Approvals Check ===')
    approvals = await db.get_all_pending_approvals()
    print(f'Pending approvals: {len(approvals)}')
    
    if approvals:
        print('\nSample approvals:')
        for a in approvals[:5]:
            request_id = a.get('request_id', 'NO_ID')
            tracking = a.get('tracking_number', 'NO_TRACKING')
            request_type = a.get('request_type', 'NO_TYPE')
            print(f'  - {request_id}: {tracking} - {request_type}')
    
    await db.close()

asyncio.run(check())
