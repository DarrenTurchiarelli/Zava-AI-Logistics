"""
Create demo parcel DT202512170037 with delivery photo for customer service demo
"""

import asyncio
import base64
from datetime import datetime, timezone
from parcel_tracking_db import ParcelTrackingDB


async def create_demo_parcel():
    """Create DT202512170037 with delivered status and photo"""
    
    print("="*70)
    print("Creating Demo Parcel: DT202512170037")
    print("="*70)
    
    async with ParcelTrackingDB() as db:
        # Check if already exists
        existing = await db.get_parcel_by_tracking_number("DT202512170037")
        if existing:
            print(f"\n⚠️  Parcel already exists:")
            print(f"   Tracking: {existing.get('tracking_number')}")
            print(f"   Barcode: {existing.get('barcode')}")
            print(f"   Status: {existing.get('status')}")
            
            # Update tracking number if needed
            if existing.get('tracking_number') != "DT202512170037":
                print(f"\n🔄 Updating tracking number to DT202512170037...")
                parcels_container = db.database.get_container_client("parcels")
                existing['tracking_number'] = "DT202512170037"
                await parcels_container.upsert_item(existing)
                print(f"   ✅ Updated!")
            
            return
        
        # Create sample delivery photo (small PNG)
        # This is a 1x1 transparent PNG
        tiny_png = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00'
            b'\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        ).decode('utf-8')
        
        # Create parcel record
        parcel_id = f"parcel_DT202512170037"
        parcel_data = {
            "id": parcel_id,
            "tracking_number": "DT202512170037",
            "barcode": "DT202512170037",
            "status": "delivered",
            "current_location": "15 High Street, Melbourne VIC 3000",
            "destination": "15 High Street, Melbourne VIC 3000",
            "estimated_delivery": "2025-12-17T15:00:00+11:00",
            "service_type": "express",
            "weight": 2.5,
            "dimensions": {"length": 30, "width": 20, "height": 15},
            "sender": {
                "name": "DT Logistics Warehouse",
                "address": "123 Distribution Drive, Melbourne VIC 3000",
                "phone": "03-9876-5432"
            },
            "recipient": {
                "name": "Sarah Johnson",
                "address": "15 High Street, Melbourne VIC 3000",
                "phone": "0412-345-678",
                "postcode": "3000"
            },
            "created_at": "2025-12-17T09:00:00+00:00",
            "delivery_photos": [
                {
                    "photo_data": tiny_png,
                    "uploaded_by": "driver001",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        
        print(f"\n📦 Creating parcel...")
        parcels_container = db.database.get_container_client("parcels")
        await parcels_container.create_item(parcel_data)
        
        print(f"✅ Parcel created successfully!")
        print(f"   Tracking Number: DT202512170037")
        print(f"   Barcode: DT202512170037")
        print(f"   Status: delivered")
        print(f"   Recipient: Sarah Johnson")
        print(f"   Location: 15 High Street, Melbourne VIC 3000")
        print(f"   Delivery Photos: 1 photo(s)")
        
        # Create tracking events
        print(f"\n📍 Creating tracking events...")
        events_container = db.database.get_container_client("tracking_events")
        
        events = [
            {
                "id": f"event_DT202512170037_registered",
                "tracking_number": "DT202512170037",
                "barcode": "DT202512170037",
                "status": "registered",
                "location": "123 Distribution Drive, Melbourne VIC 3000",
                "description": "Parcel registered and accepted",
                "timestamp": "2025-12-17T09:00:00+00:00",
                "scanned_by": "admin"
            },
            {
                "id": f"event_DT202512170037_sorted",
                "tracking_number": "DT202512170037",
                "barcode": "DT202512170037",
                "status": "sorted",
                "location": "Melbourne Sorting Facility",
                "description": "Parcel sorted for delivery",
                "timestamp": "2025-12-17T10:30:00+00:00",
                "scanned_by": "sorter001"
            },
            {
                "id": f"event_DT202512170037_out_for_delivery",
                "tracking_number": "DT202512170037",
                "barcode": "DT202512170037",
                "status": "out_for_delivery",
                "location": "Melbourne CBD",
                "description": "Out for delivery with driver001",
                "timestamp": "2025-12-17T13:00:00+00:00",
                "scanned_by": "driver001"
            },
            {
                "id": f"event_DT202512170037_delivered",
                "tracking_number": "DT202512170037",
                "barcode": "DT202512170037",
                "status": "delivered",
                "location": "15 High Street, Melbourne VIC 3000",
                "description": "Delivered successfully - photo proof captured",
                "timestamp": "2025-12-17T14:45:00+00:00",
                "scanned_by": "driver001"
            }
        ]
        
        for event in events:
            await events_container.create_item(event)
        
        print(f"✅ Created {len(events)} tracking events")
        
        print("\n" + "="*70)
        print("✅ SUCCESS - Demo parcel ready for customer service chatbot!")
        print("="*70)
        print("\nYou can now test with: 'Can I get proof of delivery on parcel DT202512170037?'")


if __name__ == "__main__":
    asyncio.run(create_demo_parcel())
