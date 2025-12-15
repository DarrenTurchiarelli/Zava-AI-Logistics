#!/usr/bin/env python3
"""
Initialize users in Azure-deployed application
This should be run once after deployment to create the users container and default accounts
"""

import asyncio
import sys
import os
from parcel_tracking_db import ParcelTrackingDB
from user_manager import UserManager

async def init_azure_users():
    """Initialize users for Azure deployment"""
    print("=" * 70)
    print("DT Logistics - Azure User Initialization")
    print("=" * 70)
    print()
    
    # Verify environment variables
    required_vars = ['COSMOS_DB_ENDPOINT', 'COSMOS_DB_KEY', 'COSMOS_DB_DATABASE_NAME']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please ensure .env file is loaded or set these variables.")
        return False
    
    print(f"✓ Environment configured")
    print(f"  Endpoint: {os.getenv('COSMOS_DB_ENDPOINT')}")
    print(f"  Database: {os.getenv('COSMOS_DB_DATABASE_NAME')}")
    print()
    
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        if not db.database:
            print("❌ Failed to connect to Cosmos DB")
            return False
        
        print("✓ Connected to Cosmos DB")
        print()
        
        # Create users container
        try:
            print("📦 Creating 'users' container...")
            await db.database.create_container(
                id="users",
                partition_key={"paths": ["/username"], "kind": "Hash"}
            )
            print("✅ Users container created successfully")
        except Exception as e:
            if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                print("✅ Users container already exists")
            else:
                print(f"❌ Error creating container: {e}")
                return False
        
        print()
        
        # Create UserManager instance
        user_mgr = UserManager(db)
        
        # Create default accounts
        print("👥 Creating default user accounts...")
        print()
        
        default_users = [
            {
                'username': 'admin',
                'password': 'admin123',
                'role': UserManager.ROLE_ADMIN,
                'full_name': 'System Administrator',
                'email': 'admin@dtlogistics.com.au'
            },
            {
                'username': 'driver001',
                'password': 'driver123',
                'role': UserManager.ROLE_DRIVER,
                'full_name': 'John Smith',
                'email': 'john.smith@dtlogistics.com.au',
                'driver_id': 'driver-001'
            },
            {
                'username': 'driver002',
                'password': 'driver123',
                'role': UserManager.ROLE_DRIVER,
                'full_name': 'Maria Garcia',
                'email': 'maria.garcia@dtlogistics.com.au',
                'driver_id': 'driver-002'
            },
            {
                'username': 'driver003',
                'password': 'driver123',
                'role': UserManager.ROLE_DRIVER,
                'full_name': 'David Wong',
                'email': 'david.wong@dtlogistics.com.au',
                'driver_id': 'driver-003'
            },
            {
                'username': 'driver004',
                'password': 'driver123',
                'role': UserManager.ROLE_DRIVER,
                'full_name': 'Test Driver (Scalability)',
                'email': 'test.driver@dtlogistics.com.au',
                'driver_id': 'driver-004'
            },
            {
                'username': 'depot_mgr',
                'password': 'depot123',
                'role': UserManager.ROLE_DEPOT_MANAGER,
                'full_name': 'Lisa Anderson',
                'email': 'lisa.anderson@dtlogistics.com.au'
            },
            {
                'username': 'support',
                'password': 'support123',
                'role': UserManager.ROLE_CUSTOMER_SERVICE,
                'full_name': 'Tom Wilson',
                'email': 'support@dtlogistics.com.au'
            }
        ]
        
        created_count = 0
        existing_count = 0
        
        for user_data in default_users:
            try:
                # Check if user already exists
                existing = await user_mgr.get_user_by_username(user_data['username'])
                if existing:
                    print(f"  ⏭️  {user_data['username']} (already exists)")
                    existing_count += 1
                    continue
                
                # Create user
                await user_mgr.create_user(
                    username=user_data['username'],
                    password=user_data['password'],
                    role=user_data['role'],
                    full_name=user_data['full_name'],
                    email=user_data.get('email'),
                    driver_id=user_data.get('driver_id')
                )
                print(f"  ✅ {user_data['username']} ({user_data['role']})")
                created_count += 1
            except Exception as e:
                print(f"  ❌ Error creating {user_data['username']}: {e}")
        
        print()
        print(f"✅ User initialization complete!")
        print(f"   Created: {created_count} users")
        print(f"   Already existed: {existing_count} users")
        print()
        
        # Display login credentials
        print("=" * 70)
        print("LOGIN CREDENTIALS")
        print("=" * 70)
        print()
        print("ADMIN:")
        print("  Username: admin")
        print("  Password: admin123")
        print()
        print("CUSTOMER SERVICE:")
        print("  Username: support")
        print("  Password: support123")
        print()
        print("DRIVERS:")
        print("  Username: driver001, driver002, driver003, driver004")
        print("  Password: driver123")
        print()
        print("DEPOT MANAGER:")
        print("  Username: depot_mgr")
        print("  Password: depot123")
        print()
        print("=" * 70)
        
        return True

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    success = asyncio.run(init_azure_users())
    sys.exit(0 if success else 1)
