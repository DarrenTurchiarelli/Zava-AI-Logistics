"""
One-time endpoint to setup users - call this from browser
Add to app.py temporarily
"""

@app.route('/admin/setup-users-now', methods=['GET'])
async def setup_users_now():
    """One-time setup endpoint to create default users"""
    try:
        async with ParcelTrackingDB() as db:
            if not db.database:
                await db.connect()
            
            # Create users container
            try:
                await db.database.create_container(
                    id="users",
                    partition_key={"paths": ["/username"], "kind": "Hash"}
                )
                print("✅ Users container created")
            except Exception as e:
                if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                    print("✅ Users container already exists")
            
            # Create UserManager and add users
            user_mgr = UserManager(db)
            
            default_users = [
                {'username': 'admin', 'password': 'admin123', 'role': UserManager.ROLE_ADMIN, 'full_name': 'Administrator'},
                {'username': 'support', 'password': 'support123', 'role': UserManager.ROLE_CUSTOMER_SERVICE, 'full_name': 'Support Agent'},
                {'username': 'driver001', 'password': 'driver123', 'role': UserManager.ROLE_DRIVER, 'full_name': 'Driver One', 'driver_id': 'driver-001'},
                {'username': 'depot_mgr', 'password': 'depot123', 'role': UserManager.ROLE_DEPOT_MANAGER, 'full_name': 'Depot Manager'},
            ]
            
            created = []
            for user_data in default_users:
                try:
                    existing = await user_mgr.get_user_by_username(user_data['username'])
                    if not existing:
                        await user_mgr.create_user(
                            username=user_data['username'],
                            password=user_data['password'],
                            role=user_data['role'],
                            full_name=user_data['full_name'],
                            driver_id=user_data.get('driver_id')
                        )
                        created.append(user_data['username'])
                except Exception as e:
                    print(f"Error creating {user_data['username']}: {e}")
            
            return f"<h1>Setup Complete!</h1><p>Created users: {', '.join(created) if created else 'All users already existed'}</p><p><a href='/login'>Go to Login</a></p>"
    
    except Exception as e:
        return f"<h1>Setup Failed</h1><p>Error: {str(e)}</p><pre>{traceback.format_exc()}</pre>", 500
