"""
Check if demo parcel DT202512170037 exists in database
"""

import asyncio
from parcel_tracking_db import ParcelTrackingDB


async def check_parcel():
    """Check if DT202512170037 exists in the database"""
    
    print("="*70)
    print("Checking for Demo Parcel: DT202512170037")
    print("="*70)
    
    async with ParcelTrackingDB() as db:
        # Try to find the parcel
        parcel = await db.get_parcel_by_tracking_number("DT202512170037")
        
        if parcel:
            print(f"\n✅ Parcel EXISTS in database")
            print(f"   Tracking Number: {parcel.get('tracking_number')}")
            print(f"   Status: {parcel.get('status')}")
            print(f"   Recipient: {parcel.get('recipient', {}).get('name', 'Unknown')}")
            print(f"   Current Location: {parcel.get('current_location', 'Unknown')}")
            
            # Check for delivery photos
            photos = parcel.get('delivery_photos', [])
            if photos:
                print(f"\n📸 Delivery Photos: {len(photos)} photo(s)")
                for idx, photo in enumerate(photos, 1):
                    print(f"   Photo {idx}:")
                    print(f"      Uploaded by: {photo.get('uploaded_by', 'unknown')}")
                    print(f"      Timestamp: {photo.get('timestamp', 'unknown')}")
                    print(f"      Size: {len(photo.get('photo_data', '')) // 1024} KB")
            else:
                print(f"\n📸 Delivery Photos: None")
        else:
            print(f"\n❌ Parcel NOT FOUND in database")
            print(f"\nThe parcel DT202512170037 needs to be created.")
            print(f"You can either:")
            print(f"  1. Use the web interface to register this parcel")
            print(f"  2. Run generate_sample_parcels.py to create demo data")
            print(f"  3. Create it manually via the camera scanner page")


if __name__ == "__main__":
    asyncio.run(check_parcel())
