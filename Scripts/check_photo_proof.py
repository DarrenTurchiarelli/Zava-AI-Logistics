import asyncio
import sys
sys.path.insert(0, 'c:\\Workbench\\dt_item_scanner')
from parcel_tracking_db import ParcelTrackingDB

async def check_parcel_photo(barcode):
    async with ParcelTrackingDB() as db:
        parcel = await db.get_parcel_by_barcode(barcode)
        if parcel:
            print(f'\n📦 Parcel Found: {parcel.get("barcode")}')
            print(f'   Status: {parcel.get("current_status")}')
            print(f'   Recipient: {parcel.get("recipient_name")}')
            print(f'   Address: {parcel.get("recipient_address")}')
            print(f'\n📸 Delivery Photos: {len(parcel.get("delivery_photos", []))} photo(s)')
            
            if parcel.get('delivery_photos'):
                for i, photo in enumerate(parcel.get('delivery_photos', [])):
                    print(f'\n   Photo {i+1}:')
                    print(f'      Uploaded by: {photo.get("uploaded_by")}')
                    print(f'      Timestamp: {photo.get("timestamp")}')
                    photo_data = photo.get("photo_data", "")
                    print(f'      Data size: {len(photo_data)} characters (base64)')
                    if len(photo_data) > 0:
                        print(f'      Estimated size: ~{len(photo_data) * 3 // 4 / 1024:.1f} KB')
            else:
                print('   ❌ No delivery photos found for this parcel')
                
            # Check status history
            if parcel.get('status_history'):
                print(f'\n📋 Status History:')
                for i, status in enumerate(parcel.get('status_history', [])[-5:]):
                    print(f'   {i+1}. {status.get("status")} - {status.get("timestamp")} ({status.get("location")})')
        else:
            print(f'❌ Parcel not found: {barcode}')

if __name__ == '__main__':
    barcode = 'DT202512220040420016'
    if len(sys.argv) > 1:
        barcode = sys.argv[1]
    
    asyncio.run(check_parcel_photo(barcode))
