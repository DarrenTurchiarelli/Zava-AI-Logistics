"""
Check what driver_state values exist in current manifests
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parcel_tracking_db import ParcelTrackingDB

async def check_manifests():
    async with ParcelTrackingDB() as db:
        manifests = await db.get_all_active_manifests()
        
        print(f"\n📊 Found {len(manifests)} active manifests")
        print("=" * 80)
        
        states_count = {}
        
        for manifest in manifests:
            driver_state = manifest.get('driver_state', 'MISSING')
            driver_id = manifest.get('driver_id')
            driver_name = manifest.get('driver_name')
            manifest_id = manifest.get('id')
            total_items = manifest.get('total_items', 0)
            
            if driver_state not in states_count:
                states_count[driver_state] = 0
            states_count[driver_state] += 1
            
            print(f"Manifest: {manifest_id[:30]}")
            print(f"  Driver: {driver_name} ({driver_id})")
            print(f"  State: {driver_state}")
            print(f"  Items: {total_items}")
            print("-" * 80)
        
        print("\n📈 Summary by State:")
        for state, count in sorted(states_count.items()):
            print(f"  {state}: {count} manifest(s)")

if __name__ == "__main__":
    asyncio.run(check_manifests())
