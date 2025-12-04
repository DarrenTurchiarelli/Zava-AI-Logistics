# User Authentication System Setup Guide

## Overview

The DT Logistics system now includes a comprehensive role-based authentication system with support for multiple user types:

- **Admin** - Full system access
- **Driver** - Access to their own manifests and deliveries
- **Depot Manager** - Manage manifests and operations
- **Customer Service** - Handle customer inquiries and approvals

## Setup Instructions

### 1. Create Users Container and Default Accounts

Run the setup script to create the users container in Cosmos DB and initialize default accounts:

```powershell
python setup_users.py
```

This will create:
- `users` container in Cosmos DB
- Default user accounts with secure password hashing

### 2. Default Login Credentials

#### Admin Access
- **Username**: `admin`
- **Password**: `admin123`
- **Permissions**: Full system access

#### Driver Accounts
- **Username**: `driver001`, `driver002`, `driver003`
- **Password**: `driver123`
- **Permissions**: View own manifests, mark deliveries complete
- **Driver IDs**: `driver-001`, `driver-002`, `driver-003`

#### Depot Manager
- **Username**: `depot_mgr`
- **Password**: `depot123`
- **Permissions**: View all manifests, create manifests, approve requests

#### Customer Service
- **Username**: `support`
- **Password**: `support123`
- **Permissions**: View parcels, handle customer inquiries

⚠️ **IMPORTANT**: Change these default passwords immediately in production!

## User Management

### Creating New Users

```python
from parcel_tracking_db import ParcelTrackingDB
from user_manager import UserManager

async def create_new_driver():
    async with ParcelTrackingDB() as db:
        user_mgr = UserManager(db)
        
        await user_mgr.create_user(
            username='driver004',
            password='secure_password_here',
            role=UserManager.ROLE_DRIVER,
            full_name='Jane Smith',
            email='jane.smith@dtlogistics.com.au',
            driver_id='driver-004'
        )
```

### Updating Passwords

```python
async def change_password():
    async with ParcelTrackingDB() as db:
        user_mgr = UserManager(db)
        await user_mgr.update_password('driver001', 'new_secure_password')
```

### Deactivating Users

```python
async def deactivate():
    async with ParcelTrackingDB() as db:
        user_mgr = UserManager(db)
        await user_mgr.deactivate_user('driver003')
```

## Role-Based Access Control

### Route Protection

Routes are protected using decorators:

```python
@app.route('/admin/manifests')
@role_required(UserManager.ROLE_ADMIN, UserManager.ROLE_DEPOT_MANAGER)
def admin_manifests():
    # Only admins and depot managers can access
    pass

@app.route('/driver/manifest')
@login_required
def driver_manifest():
    # All logged-in users, but drivers see only their own data
    user = session.get('user')
    if user.get('role') == UserManager.ROLE_DRIVER:
        driver_id = user.get('driver_id')
    pass
```

### Permission Checks

Use utility functions to check permissions:

```python
from user_manager import is_admin, is_driver, can_view_all_manifests

user = session.get('user')

if is_admin(user):
    # Admin-only actions
    pass

if can_view_all_manifests(user):
    # Show all manifests
    pass
else:
    # Show only user's own data
    pass
```

## User Roles and Permissions

| Feature | Admin | Depot Manager | Driver | Customer Service |
|---------|-------|---------------|--------|------------------|
| View All Manifests | ✅ | ✅ | ❌ | ❌ |
| Create Manifests | ✅ | ✅ | ❌ | ❌ |
| View Own Manifest | ✅ | ✅ | ✅ | ❌ |
| Mark Deliveries Complete | ✅ | ✅ | ✅ (own only) | ❌ |
| Approve Requests | ✅ | ✅ | ❌ | ❌ |
| View All Parcels | ✅ | ✅ | ❌ | ✅ |
| Register Parcels | ✅ | ✅ | ❌ | ✅ |
| Fraud Detection | ✅ | ✅ | ❌ | ✅ |

## Security Features

### Password Security
- **PBKDF2-HMAC-SHA256** hashing with 100,000 iterations
- **Random salt** per user (16 bytes)
- Passwords never stored in plain text

### Session Management
- Secure session cookies
- User info stored in session after login
- Role-based redirect after authentication

### Authorization
- Decorator-based route protection
- Role-based access control
- Per-resource permission checks

## Login Flow

1. User enters credentials at `/login`
2. System authenticates against `users` container
3. Password verified using PBKDF2 hash
4. User object stored in session (without password)
5. User redirected based on role:
   - **Drivers** → `/driver/manifest` (their manifest)
   - **Others** → `/dashboard` (admin dashboard)

## Driver-Specific Features

### Auto-Assignment to Manifests

Drivers automatically see only manifests assigned to their `driver_id`:

```python
user = session.get('user')
if user.get('role') == UserManager.ROLE_DRIVER:
    driver_id = user.get('driver_id')  # e.g., 'driver-001'
    manifest = await db.get_driver_manifest(driver_id)
```

### Delivery Restrictions

Drivers can only mark their own deliveries complete:

```python
@app.route('/driver/manifest/<manifest_id>/complete/<barcode>', methods=['POST'])
@login_required
def mark_delivery_complete(manifest_id, barcode):
    user = session.get('user')
    
    if user.get('role') == UserManager.ROLE_DRIVER:
        # Verify manifest belongs to this driver
        manifest = await db.get_manifest_by_id(manifest_id)
        if manifest.get('driver_id') != user.get('driver_id'):
            return error("Permission denied")
```

## Testing the System

### Test Driver Login

1. Start Flask app: `$env:FLASK_ENV='development'; python app.py`
2. Navigate to: http://127.0.0.1:5000/login
3. Login as driver:
   - Username: `driver001`
   - Password: `driver123`
4. Should redirect to `/driver/manifest`
5. Should see manifest for driver-001 only

### Test Admin Access

1. Login as admin:
   - Username: `admin`
   - Password: `admin123`
2. Should have access to all routes
3. Can view all manifests at `/admin/manifests`

## Production Deployment

### Environment Variables

```bash
# Strong secret key for session encryption
FLASK_SECRET_KEY="generate-strong-random-key-here"

# Cosmos DB credentials
COSMOS_DB_ENDPOINT="..."
COSMOS_DB_KEY="..."
```

### Security Checklist

- [ ] Change all default passwords
- [ ] Generate strong `FLASK_SECRET_KEY`
- [ ] Enable HTTPS in production
- [ ] Set secure cookie flags
- [ ] Implement password complexity rules
- [ ] Add rate limiting for login attempts
- [ ] Enable session timeout
- [ ] Add two-factor authentication (optional)
- [ ] Regular security audits
- [ ] Monitor failed login attempts

## Troubleshooting

### "User not found" Error

- Ensure `setup_users.py` was run successfully
- Check `users` container exists in Cosmos DB
- Verify network connectivity to Cosmos DB

### Driver Can't See Manifest

- Verify driver's `driver_id` matches manifest's `driver_id`
- Check manifest exists with `status='active'`
- Ensure manifest date matches today

### Permission Denied

- Check user's role in session
- Verify route decorator matches user role
- Review permission helper functions

## Next Steps

1. Run `python setup_users.py` to create users
2. Test login with default credentials
3. Change default passwords
4. Create additional users as needed
5. Configure production security settings
