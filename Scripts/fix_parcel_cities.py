"""Fix destination_city for existing parcels by re-parsing addresses"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parcel_tracking_db import ParcelTrackingDB

async def fix_destination_cities():
    """Update destination_city for all parcels by re-parsing addresses"""
    async with ParcelTrackingDB() as db:
        await db.connect()
        
        container = db.database.get_container_client(db.parcels_container)
        
        # Get all parcels
        query = "SELECT * FROM c"
        parcels = []
        async for parcel in container.query_items(query=query):
            parcels.append(parcel)
        
        print(f"📦 Found {len(parcels)} parcels to fix")
        
        updated = 0
        for parcel in parcels:
            # Parse the recipient address to extract city
            address = parcel.get('recipient_address', '')
            address_parts = address.split(',')
            
            # Extract city from address
            # Format: "123 Street Name, City STATE POSTCODE" (2 parts after split)
            # or "123 Street, Suburb, City STATE POSTCODE" (3+ parts)
            if len(address_parts) >= 2:
                # Get the last part which contains "City STATE POSTCODE"
                last_part = address_parts[-1].strip()
                # Extract just the city name (first word before STATE)
                city_state_postcode = last_part.split()
                destination_city = city_state_postcode[0] if city_state_postcode else parcel.get('destination_state', 'Unknown')
            else:
                destination_city = parcel.get('destination_state', 'Unknown')
            
            # Update if different
            if parcel.get('destination_city') != destination_city:
                parcel['destination_city'] = destination_city
                await container.replace_item(item=parcel['id'], body=parcel)
                updated += 1
                if updated % 100 == 0:
                    print(f"   ✅ Updated {updated} parcels...")
        
        print(f"\n✅ Fixed destination_city for {updated} parcels")
        
        # Show sample
        print(f"\n📍 Sample parcels after fix:")
        sample = parcels[:5]
        for p in sample:
            print(f"   {p['barcode']}: {p.get('recipient_address')} → City: {p.get('destination_city')}")

if __name__ == '__main__':
    asyncio.run(fix_destination_cities())
