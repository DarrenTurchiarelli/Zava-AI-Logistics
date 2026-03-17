"""
Setup users container and create default accounts
Run this once to initialize the user management system
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

import asyncio

from parcel_tracking_db import ParcelTrackingDB
from user_manager import UserManager


async def setup_users_container():
    """Create users container and default accounts"""
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()

        try:
            # Create users container
            print("[SETUP] Creating 'users' container...")
            await db.database.create_container(id="users", partition_key={"paths": ["/username"], "kind": "Hash"})
            print("[OK] Users container created successfully")
        except Exception as e:
            if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                print("[OK] Users container already exists")
            else:
                print(f"[WARN] Error creating container: {e}")

        # Create UserManager instance
        user_mgr = UserManager(db)

        # Create default accounts
        print("\n[SETUP] Creating default user accounts...")

        default_users = [
            {
                "username": "admin",
                "password": "admin123",
                "role": UserManager.ROLE_ADMIN,
                "full_name": "System Administrator",
                "email": "admin@dtlogistics.com.au",
            },
            {
                "username": "driver001",
                "password": "driver123",
                "role": UserManager.ROLE_DRIVER,
                "full_name": "John Smith",
                "email": "john.smith@dtlogistics.com.au",
                "driver_id": "driver-001",
            },
            {
                "username": "driver002",
                "password": "driver123",
                "role": UserManager.ROLE_DRIVER,
                "full_name": "Sarah Jones",
                "email": "sarah.jones@dtlogistics.com.au",
                "driver_id": "driver-002",
            },
            {
                "username": "driver003",
                "password": "driver123",
                "role": UserManager.ROLE_DRIVER,
                "full_name": "Mike Brown",
                "email": "mike.brown@dtlogistics.com.au",
                "driver_id": "driver-003",
            },
            {
                "username": "depot_mgr",
                "password": "depot123",
                "role": UserManager.ROLE_DEPOT_MANAGER,
                "full_name": "Lisa Anderson",
                "email": "lisa.anderson@dtlogistics.com.au",
            },
            {
                "username": "support",
                "password": "support123",
                "role": UserManager.ROLE_CUSTOMER_SERVICE,
                "full_name": "Tom Wilson",
                "email": "support@dtlogistics.com.au",
            },
        ]

        for user_data in default_users:
            try:
                # Check if user already exists
                existing = await user_mgr.get_user_by_username(user_data["username"])
                if existing:
                    print(f"[SKIP] User '{user_data['username']}' already exists")
                    continue

                # Create user
                await user_mgr.create_user(
                    username=user_data["username"],
                    password=user_data["password"],
                    role=user_data["role"],
                    full_name=user_data["full_name"],
                    email=user_data.get("email"),
                    driver_id=user_data.get("driver_id"),
                )
                print(f"[OK] Created user: {user_data['username']} ({user_data['role']})")

            except Exception as e:
                print(f"[ERROR] Error creating user '{user_data['username']}': {e}")

        print("\n" + "=" * 80)
        print("[SUCCESS] USER SETUP COMPLETE")
        print("=" * 80)
        print("\nDefault Login Credentials:")
        print("\nADMIN:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nDRIVERS:")
        print("  Username: driver001, driver002, driver003")
        print("  Password: driver123")
        print("\nDEPOT MANAGER:")
        print("  Username: depot_mgr")
        print("  Password: depot123")
        print("\nCUSTOMER SERVICE:")
        print("  Username: support")
        print("  Password: support123")
        print("\n[IMPORTANT] Change these passwords in production!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(setup_users_container())
