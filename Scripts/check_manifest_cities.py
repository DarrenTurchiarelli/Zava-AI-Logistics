"""Check manifest details for driver-001"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parcel_tracking_db import ParcelTrackingDB

async def check_manifest():
    """Check driver-001 manifest"""
    async with ParcelTrackingDB() as db:
        await db.connect()
        
        manifest = await db.get_driver_manifest('driver-001')
        
        if manifest:
            print(f"✅ Found manifest for driver-001")
            print(f"   - ID: {manifest.get('id')}")
            print(f"   - Driver: {manifest.get('driver_name')}")
            print(f"   - Driver Location: {manifest.get('driver_location')}")
            print(f"   - Driver State: {manifest.get('driver_state')}")
            print(f"   - Total Parcels: {len(manifest.get('items', []))}")
            
            # Check destination cities of parcels
            cities = {}
            for item in manifest.get('items', [])[:10]:  # Check first 10
                city = item.get('destination_city', 'None')
                state = item.get('destination_state', 'None')
                full_loc = f"{city}, {state}"
                cities[full_loc] = cities.get(full_loc, 0) + 1
                
            print(f"\n📍 Sample parcel destinations:")
            for loc, count in list(cities.items())[:5]:
                print(f"   - {loc}: {count} parcels")
        else:
            print(f"❌ No manifest found for driver-001")

if __name__ == '__main__':
    asyncio.run(check_manifest())
