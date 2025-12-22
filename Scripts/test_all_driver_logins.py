"""Test driver logins and manifest access for all drivers"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parcel_tracking_db import ParcelTrackingDB
from user_manager import UserManager

async def test_all_drivers():
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        print("="*70)
        print("🧪 Testing Driver Logins and Manifest Access")
        print("="*70)
        
        # Test driver logins from login.html
        test_drivers = ['driver001', 'driver002', 'driver003', 'driver004']
        
        user_mgr = UserManager(db)
        
        for username in test_drivers:
            print(f"\n📋 Testing: {username}")
            print("-" * 70)
            
            # Check if user exists
            user = await user_mgr.get_user_by_username(username)
            if user:
                driver_id = user.get('driver_id')
                print(f"   ✅ User exists")
                print(f"      Username: {username}")
                print(f"      Full Name: {user.get('full_name')}")
                print(f"      Driver ID: {driver_id}")
                print(f"      Role: {user.get('role')}")
                
                # Check for manifest
                if driver_id:
                    manifest = await db.get_driver_manifest(driver_id)
                    if manifest:
                        print(f"   ✅ Manifest exists")
                        print(f"      Manifest ID: {manifest.get('id')}")
                        print(f"      Driver Location: {manifest.get('driver_location')}")
                        print(f"      Driver State: {manifest.get('driver_state')}")
                        print(f"      Total Items: {manifest.get('total_items')}")
                        
                        # Test the filtering logic
                        driver_location = manifest.get('driver_location')
                        driver_state = manifest.get('driver_state', 'NSW')
                        
                        if manifest.get('items'):
                            items = manifest['items']
                            original_count = len(items)
                            
                            # Apply same filter as app.py
                            filtered_items = [
                                item for item in items
                                if (driver_location and (item.get('destination_city') or '').lower() == str(driver_location).lower()) or 
                                   (not item.get('destination_city') and item.get('destination_state') == driver_state)
                            ]
                            filtered_count = len(filtered_items)
                            
                            print(f"   ✅ Filtering works: {original_count} → {filtered_count} items")
                        else:
                            print(f"   ⚠️  No items in manifest")
                    else:
                        print(f"   ⚠️  No manifest found for {driver_id}")
                else:
                    print(f"   ⚠️  No driver_id mapped for {username}")
            else:
                print(f"   ❌ User does not exist")
                print(f"      Need to create: {username} → driver-{username[-3:]}")
        
        # Test depot manager (not a driver)
        print(f"\n📋 Testing: depot_mgr (non-driver)")
        print("-" * 70)
        depot_user = await user_mgr.get_user_by_username('depot_mgr')
        if depot_user:
            print(f"   ✅ Depot manager exists")
            print(f"      Username: depot_mgr")
            print(f"      Full Name: {depot_user.get('full_name')}")
            print(f"      Role: {depot_user.get('role')}")
            print(f"      Driver ID: {depot_user.get('driver_id', 'N/A')}")
        else:
            print(f"   ❌ Depot manager does not exist")
        
        print("\n" + "="*70)
        print("📊 Summary")
        print("="*70)
        
        # Count active manifests
        container = db.database.get_container_client("driver_manifests")
        query = "SELECT * FROM c WHERE c.status = 'active'"
        
        manifests = []
        async for m in container.query_items(query=query):
            manifests.append(m)
        
        print(f"Total active manifests: {len(manifests)}")
        print(f"\nDriver IDs with manifests:")
        for m in sorted(manifests, key=lambda x: x.get('driver_id', '')):
            print(f"   - {m.get('driver_id')}: {m.get('driver_name')} ({m.get('total_items')} items)")

if __name__ == "__main__":
    asyncio.run(test_all_drivers())
