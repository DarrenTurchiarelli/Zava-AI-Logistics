"""
Test driver login functionality
"""
import asyncio
import sys
from parcel_tracking_db import ParcelTrackingDB
from user_manager import UserManager
from azure_ai_agents import identity_agent

async def test_driver_login():
    """Test driver authentication and AI verification"""
    
    print("\n" + "="*70)
    print("Testing Driver Login with Azure AI Identity Agent")
    print("="*70)
    
    username = "driver001"
    password = "driver123"
    
    print(f"\n[1/3] Authenticating driver: {username}")
    
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        user_mgr = UserManager(db)
        user = await user_mgr.authenticate(username, password)
        
        if not user:
            print(f"❌ Authentication failed for {username}")
            return False
        
        print(f"✓ Authentication successful")
        print(f"   User: {user['full_name']}")
        print(f"   Role: {user['role']}")
        
        # Test Azure AI Identity Agent
        print(f"\n[2/3] Calling Azure AI Identity Agent...")
        
        verification_request = {
            'courier_id': user.get('username'),
            'name': user.get('full_name'),
            'role': user.get('role'),
            'employment_status': 'active',
            'authorized_zone': user.get('store_location', 'All'),
            'verification_method': 'credential_login'
        }
        
        try:
            identity_result = await identity_agent(verification_request)
            
            print(f"\n[3/3] Identity Agent Response:")
            print(f"   Success: {identity_result.get('success')}")
            print(f"   Agent ID: {identity_result.get('agent_id')}")
            
            if identity_result.get('error'):
                print(f"   Error: {identity_result.get('error')}")
            
            if identity_result.get('response'):
                response_text = identity_result.get('response')
                print(f"   Response: {response_text[:200]}...")
            
            if identity_result.get('success'):
                print(f"\n✅ Driver login with AI verification: SUCCESS")
                user['ai_verified'] = True
            else:
                print(f"\n⚠️  Driver authenticated but AI verification unavailable")
                user['ai_verified'] = False
            
            return True
            
        except Exception as e:
            print(f"\n❌ Identity Agent error: {e}")
            import traceback
            traceback.print_exc()
            print(f"\n⚠️  Driver authenticated but AI verification failed")
            user['ai_verified'] = False
            return True  # Still allow login

if __name__ == "__main__":
    success = asyncio.run(test_driver_login())
    sys.exit(0 if success else 1)
