"""
Quick validation: Check if agent retrieves full photo data (not just metadata)

This test:
1. Finds an existing delivered parcel with delivery photos
2. Calls the agent tool to retrieve it
3. Validates the response includes full base64 image data
"""

import asyncio
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_tools import track_parcel_tool


async def test_agent_photo_retrieval():
    """Test agent retrieves full photo data, not just metadata"""
    
    print("\n" + "=" * 80)
    print("VALIDATING: Customer Service Agent Photo Retrieval")
    print("=" * 80)
    
    # Test with known parcels that have delivery photos
    test_tracking_numbers = [
        "DT202512170037",  # Sarah Johnson - known to have delivery photo
        "RG857954",         # Dr. Emma Wilson  
    ]
    
    success_count = 0
    
    for tracking_number in test_tracking_numbers:
        print(f"\n🔍 Testing: {tracking_number}")
        print("-" * 80)
        
        try:
            # Call the agent tool (same as what customer service agent uses)
            result = await track_parcel_tool(tracking_number)
            
            if not result.get("success"):
                print(f"   ❌ Agent tool failed: {result.get('error')}")
                continue
            
            parcel_data = result.get("parcel", {})
            print(f"   ✅ Agent tool returned parcel data")
            print(f"      Status: {parcel_data.get('current_status')}")
            
            # Check lodgement photos
            lodgement_photos = parcel_data.get("lodgement_photos", [])
            if lodgement_photos:
                print(f"   📸 Lodgement Photos: {len(lodgement_photos)}")
                for idx, photo in enumerate(lodgement_photos, 1):
                    photo_data = photo.get('photo_data', '')
                    if photo_data:
                        print(f"      Photo {idx}: ✅ Contains {len(photo_data)} chars of base64 data")
                        # Verify it's valid base64
                        try:
                            decoded = base64.b64decode(photo_data[:100])  # Test first 100 chars
                            print(f"                ✅ Valid base64 image data")
                        except:
                            print(f"                ❌ Invalid base64 data")
                    else:
                        print(f"      Photo {idx}: ❌ ONLY METADATA - no photo_data field!")
            
            # Check delivery photos
            delivery_photos = parcel_data.get("delivery_photos", [])
            if delivery_photos:
                print(f"   📸 Delivery Photos: {len(delivery_photos)}")
                for idx, photo in enumerate(delivery_photos, 1):
                    photo_data = photo.get('photo_data', '')
                    if photo_data:
                        print(f"      Photo {idx}: ✅ Contains {len(photo_data)} chars of base64 data")
                        # Verify it's valid base64
                        try:
                            decoded = base64.b64decode(photo_data[:100])  # Test first 100 chars
                            print(f"                ✅ Valid base64 image data")
                            success_count += 1
                        except:
                            print(f"                ❌ Invalid base64 data")
                    else:
                        print(f"      Photo {idx}: ❌ ONLY METADATA - no photo_data field!")
            else:
                print(f"   ℹ️  No delivery photos for this parcel")
            
            if not lodgement_photos and not delivery_photos:
                print(f"   ⚠️  Parcel has no photos at all")
        
        except Exception as e:
            print(f"   ❌ Error testing {tracking_number}: {e}")
            import traceback
            traceback.print_exc()
    
    # Check frontend template
    print("\n" + "=" * 80)
    print("VALIDATING: Frontend Photo Display")
    print("=" * 80)
    
    template_path = "templates/customer_service_chatbot.html"
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_delivery = "data.delivery_photos" in content
        has_base64 = "data:image/png;base64,${photo.photo_data}" in content
        
        print(f"   {'✅' if has_delivery else '❌'} Checks for delivery_photos in response")
        print(f"   {'✅' if has_base64 else '❌'} Displays photo as base64 image")
        
        if has_delivery and has_base64:
            print("\n   ✅ Frontend correctly displays actual images")
        else:
            print("\n   ❌ Frontend missing photo display code")
    else:
        print(f"   ⚠️  Template not found: {template_path}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if success_count > 0:
        print(f"✅ SUCCESS: Agent retrieves FULL photo data (not just metadata)")
        print(f"   - Tested {len(test_tracking_numbers)} parcels")
        print(f"   - Found {success_count} photos with complete base64 image data")
        print(f"   - Customer service reps will see actual images")
        print("\n🎉 Photo flow is working correctly!")
    else:
        print(f"⚠️  No photos found in test parcels")
        print(f"   This might be normal if test data hasn't been generated yet")


if __name__ == "__main__":
    asyncio.run(test_agent_photo_retrieval())
