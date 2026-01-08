"""Check if driver user exists and what driver_id they have"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parcel_tracking_db import ParcelTrackingDB
from user_manager import UserManager

async def check_driver_user():
    """Check driver001 user details"""
    async with ParcelTrackingDB() as db:
        await db.connect()
        user_mgr = UserManager(db)
        
        # Get user by username
        user = await user_mgr.get_user_by_username('driver001')
        
        if user:
            print(f"✅ User 'driver001' exists")
            print(f"   - ID: {user.get('id')}")
            print(f"   - Username: {user.get('username')}")
            print(f"   - Role: {user.get('role')}")
            print(f"   - Full Name: {user.get('full_name')}")
            print(f"   - Driver ID: {user.get('driver_id')}")
            print(f"   - Active: {user.get('active')}")
        else:
            print(f"❌ User 'driver001' does NOT exist")
            print(f"   Need to create user with driver_id='driver-001'")
        
        # Also check what manifests exist for driver-001
        print(f"\nChecking manifests for driver_id='driver-001':")
        manifests = await db.get_driver_manifest('driver-001')
        
        if manifests:
            print(f"✅ Found manifest for driver-001")
            print(f"   - ID: {manifests.get('id')}")
            print(f"   - Driver: {manifests.get('driver_name')}")
            print(f"   - Parcels: {len(manifests.get('items', []))}")
            print(f"   - Status: {manifests.get('status')}")
        else:
            print(f"❌ No manifest found for driver-001")

if __name__ == '__main__':
    asyncio.run(check_driver_user())
