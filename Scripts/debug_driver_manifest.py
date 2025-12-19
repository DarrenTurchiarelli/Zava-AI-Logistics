#!/usr/bin/env python3
"""
Debug script to check driver manifest state
"""
import asyncio
import sys
sys.path.insert(0, '..')

from parcel_tracking_db import ParcelTrackingDB

async def main():
    """Check current manifest state for Maria Garcia"""
    async with ParcelTrackingDB() as db:
        # Check for Maria Garcia (driver-002)
        driver_id = 'driver-002'
        manifest = await db.get_driver_manifest(driver_id)
        
        if not manifest:
            print(f"❌ No manifest found for driver {driver_id}")
            return
        
        print(f"\n📋 Manifest for {manifest.get('driver_name', 'Unknown')}")
        print(f"   ID: {manifest.get('id')}")
        print(f"   Date: {manifest.get('manifest_date')}")
        print(f"   Status: {manifest.get('status')}")
        print(f"   Items: {len(manifest.get('items', []))}")
        print(f"\n🗺️ Route Information:")
        print(f"   route_optimized: {manifest.get('route_optimized')}")
        print(f"   optimized_route exists: {bool(manifest.get('optimized_route'))}")
        print(f"   optimized_route length: {len(manifest.get('optimized_route', []))}")
        print(f"   selected_route_type: {manifest.get('selected_route_type')}")
        print(f"   estimated_distance_km: {manifest.get('estimated_distance_km')}")
        print(f"   estimated_duration_minutes: {manifest.get('estimated_duration_minutes')}")
        print(f"   all_routes exists: {bool(manifest.get('all_routes'))}")
        
        if manifest.get('all_routes'):
            print(f"\n📊 Available route options:")
            for route_type, route_data in manifest.get('all_routes', {}).items():
                print(f"   - {route_type}: {route_data.get('total_distance_km')} km, {route_data.get('total_duration_minutes')} min")
        
        # Check items
        if manifest.get('items'):
            print(f"\n📦 First few items:")
            for idx, item in enumerate(manifest['items'][:3], 1):
                print(f"   {idx}. {item.get('recipient_name')} - {item.get('recipient_address')}")

if __name__ == '__main__':
    asyncio.run(main())
