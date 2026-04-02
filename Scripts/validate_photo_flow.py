"""
Validate driver photo upload and customer service photo retrieval flow.

Tests:
1. Driver marks delivery complete with photo
2. Photo is correctly stored in Cosmos DB
3. Customer service agent retrieves photo with full base64 data
4. Frontend displays actual photo (not just metadata)
"""

import asyncio
import base64
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parcel_tracking_db import ParcelTrackingDB
from agent_tools import track_parcel_tool


def generate_test_photo():
    """Generate a small test PNG image (1x1 red pixel)"""
    # This is a valid 1x1 red PNG image in base64
    tiny_red_png = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    return tiny_red_png


async def test_driver_photo_upload():
    """Test 1: Validate driver can upload delivery photo"""
    print("\n" + "=" * 80)
    print("TEST 1: Driver Photo Upload")
    print("=" * 80)
    
    async with ParcelTrackingDB() as db:
        # Find a delivered parcel without photos
        container = db.database.get_container_client(db.parcels_container)
        
        query = """
        SELECT TOP 1 c.barcode, c.tracking_number
        FROM c 
        WHERE c.type = 'parcel' 
        AND c.current_status = 'Delivered'
        AND (NOT IS_DEFINED(c.delivery_photos) OR ARRAY_LENGTH(c.delivery_photos) = 0)
        ORDER BY c.created_at DESC
        """
        
        parcels = container.query_items(query=query, enable_cross_partition_query=True)
        parcel_list = list(parcels)
        
        if not parcel_list:
            print("❌ No delivered parcels without photos found")
            print("   Creating test parcel...")
            # We'll use an existing parcel for testing
            return None
        
        test_parcel = parcel_list[0]
        barcode = test_parcel['barcode']
        tracking_num = test_parcel['tracking_number']
        
        print(f"✅ Found test parcel: {tracking_num} (barcode: {barcode})")
        
        # Generate test photo
        photo_data = generate_test_photo()
        print(f"✅ Generated test photo (base64 length: {len(photo_data)} characters)")
        
        # Store photo using driver upload method
        success = await db.store_delivery_photo(
            barcode=barcode,
            photo_base64=photo_data,
            uploaded_by="test_driver"
        )
        
        if success:
            print(f"✅ Photo successfully stored for {tracking_num}")
            
            # Verify photo in database
            parcel = await db.get_parcel_by_barcode(barcode)
            delivery_photos = parcel.get("delivery_photos", [])
            
            if delivery_photos:
                print(f"✅ Verified: {len(delivery_photos)} delivery photo(s) in database")
                latest_photo = delivery_photos[-1]
                print(f"   - Uploaded by: {latest_photo.get('uploaded_by')}")
                print(f"   - Timestamp: {latest_photo.get('timestamp')}")
                print(f"   - Photo data length: {len(latest_photo.get('photo_data', ''))} characters")
                print(f"   - Has complete base64: {latest_photo.get('photo_data', '').startswith('iVBOR')}")
                return tracking_num
            else:
                print("❌ Photo not found in database after storage")
                return None
        else:
            print(f"❌ Failed to store photo for {tracking_num}")
            return None


async def test_agent_photo_retrieval(tracking_number):
    """Test 2: Validate customer service agent retrieves full photo data"""
    print("\n" + "=" * 80)
    print("TEST 2: Customer Service Agent Photo Retrieval")
    print("=" * 80)
    
    if not tracking_number:
        print("⚠️  Skipping - no test parcel available")
        return False
    
    print(f"🔍 Retrieving parcel data for: {tracking_number}")
    
    # Call the agent tool (same as what customer service agent uses)
    result = await track_parcel_tool(tracking_number)
    
    if result.get("success"):
        parcel_data = result.get("parcel", {})
        print(f"✅ Agent tool returned parcel data")
        print(f"   - Tracking number: {parcel_data.get('tracking_number')}")
        print(f"   - Status: {parcel_data.get('current_status')}")
        
        delivery_photos = parcel_data.get("delivery_photos", [])
        
        if delivery_photos:
            print(f"✅ Agent tool returned {len(delivery_photos)} delivery photo(s)")
            
            for idx, photo in enumerate(delivery_photos, 1):
                print(f"\n   Photo {idx}:")
                print(f"   - Uploaded by: {photo.get('uploaded_by')}")
                print(f"   - Timestamp: {photo.get('timestamp')}")
                print(f"   - Photo data present: {'photo_data' in photo}")
                
                photo_data = photo.get('photo_data', '')
                if photo_data:
                    print(f"   - Photo data length: {len(photo_data)} characters")
                    print(f"   - Is valid base64 PNG: {photo_data.startswith('iVBOR')}")
                    print(f"   - First 50 chars: {photo_data[:50]}...")
                    
                    # Validate it's truly base64-decodable
                    try:
                        decoded = base64.b64decode(photo_data)
                        print(f"   - Decoded size: {len(decoded)} bytes")
                        print(f"   ✅ Photo data is valid and complete")
                    except Exception as e:
                        print(f"   ❌ Photo data is not valid base64: {e}")
                        return False
                else:
                    print(f"   ❌ Photo data is EMPTY - only metadata returned!")
                    return False
            
            return True
        else:
            print("❌ No delivery photos returned by agent tool")
            return False
    else:
        print(f"❌ Agent tool failed: {result.get('error')}")
        return False


async def test_frontend_display_capability():
    """Test 3: Validate frontend can display photos"""
    print("\n" + "=" * 80)
    print("TEST 3: Frontend Display Capability")
    print("=" * 80)
    
    # Check customer service template has photo display code
    template_path = "templates/customer_service_chatbot.html"
    
    if not os.path.exists(template_path):
        print(f"❌ Template not found: {template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for key photo display elements
    checks = {
        "Photo display check": "data.delivery_photos" in content,
        "Base64 img src": "data:image/png;base64,${photo.photo_data}" in content,
        "Photo loop": "delivery_photos.forEach" in content,
        "Photo metadata": "photo.uploaded_by" in content,
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}: {'PASSED' if passed else 'FAILED'}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ Frontend has complete photo display implementation")
        print("   Photos will be shown as actual images, not just metadata")
    else:
        print("\n❌ Frontend missing photo display code")
    
    return all_passed


async def main():
    """Run all validation tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "PHOTO FLOW VALIDATION TEST SUITE" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        # Test 1: Driver uploads photo
        tracking_number = await test_driver_photo_upload()
        
        # Test 2: Agent retrieves photo with full data
        agent_test_passed = await test_agent_photo_retrieval(tracking_number)
        
        # Test 3: Frontend can display photos
        frontend_test_passed = await test_frontend_display_capability()
        
        # Summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        
        if tracking_number:
            print(f"✅ Driver photo upload: WORKING")
        else:
            print(f"⚠️  Driver photo upload: SKIPPED (no test data)")
        
        if agent_test_passed:
            print(f"✅ Agent photo retrieval: WORKING (full base64 data included)")
        else:
            print(f"❌ Agent photo retrieval: FAILED (missing or incomplete photo data)")
        
        if frontend_test_passed:
            print(f"✅ Frontend photo display: IMPLEMENTED")
        else:
            print(f"❌ Frontend photo display: NOT IMPLEMENTED")
        
        if agent_test_passed and frontend_test_passed:
            print("\n" + "🎉 " * 20)
            print("✅ ALL TESTS PASSED!")
            print("   - Drivers can upload photos")
            print("   - Agent retrieves complete photo data (not just metadata)")
            print("   - Frontend displays actual images to customer service reps")
            print("🎉 " * 20)
        else:
            print("\n⚠️  Some tests failed - review output above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
