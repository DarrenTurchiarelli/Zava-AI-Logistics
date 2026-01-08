"""
Generate Demo Parcels for Dispatcher Agent
============================================

Creates parcels with "At Depot" status ready for the Dispatcher Agent to assign to drivers.
Run this script between demos to replenish the pool of parcels for assignment.

Usage:
    python Scripts/generate_dispatcher_demo_data.py

This creates 50 parcels per day (today + tomorrow) with status "At Depot" (ready for assignment) distributed across:
- Sydney, NSW (20 parcels)
- Melbourne, VIC (15 parcels)
- Brisbane, QLD (10 parcels)
- Adelaide, SA (5 parcels)
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add root directory to path (go up 2 levels from utils/generators)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from parcel_tracking_db import ParcelTrackingDB


# Sample addresses for each city
DEMO_ADDRESSES = {
    "Sydney": [
        {"name": "Sarah Johnson", "address": "1 Macquarie Street, Sydney NSW 2000", "phone": "+61 2 9999 0001"},
        {"name": "Michael Chen", "address": "88 Cumberland Street, The Rocks NSW 2000", "phone": "+61 2 9999 0002"},
        {"name": "Emma Wilson", "address": "483 George Street, Sydney NSW 2000", "phone": "+61 2 9999 0003"},
        {"name": "James Martinez", "address": "201 Kent Street, Sydney NSW 2000", "phone": "+61 2 9999 0004"},
        {"name": "Olivia Brown", "address": "100 Market Street, Sydney NSW 2000", "phone": "+61 2 9999 0005"},
        {"name": "William Taylor", "address": "456 Kent Street, Sydney NSW 2000", "phone": "+61 2 9999 0006"},
        {"name": "Sophia Anderson", "address": "200 Barangaroo Avenue, Barangaroo NSW 2000", "phone": "+61 2 9999 0007"},
        {"name": "Benjamin Lee", "address": "1 Bligh Street, Sydney NSW 2000", "phone": "+61 2 9999 0008"},
        {"name": "Isabella Martinez", "address": "181 Miller Street, North Sydney NSW 2060", "phone": "+61 2 9999 0009"},
        {"name": "Mason Davis", "address": "1 Denison Street, North Sydney NSW 2060", "phone": "+61 2 9999 0010"},
    ],
    "Melbourne": [
        {"name": "Oliver Thompson", "address": "120 Collins Street, Melbourne VIC 3000", "phone": "+61 3 9999 0001"},
        {"name": "Emma Wilson", "address": "1 Flinders Street, Melbourne VIC 3000", "phone": "+61 3 9999 0002"},
        {"name": "Noah Brown", "address": "8 Exhibition Street, Melbourne VIC 3000", "phone": "+61 3 9999 0003"},
        {"name": "Sophia Martin", "address": "501 Swanston Street, Melbourne VIC 3000", "phone": "+61 3 9999 0004"},
        {"name": "Liam Davis", "address": "181 William Street, Melbourne VIC 3000", "phone": "+61 3 9999 0005"},
    ],
    "Brisbane": [
        {"name": "Ava Johnson", "address": "100 Queen Street, Brisbane QLD 4000", "phone": "+61 7 9999 0001"},
        {"name": "William Taylor", "address": "12 Creek Street, Brisbane QLD 4000", "phone": "+61 7 9999 0002"},
        {"name": "Isabella White", "address": "45 Eagle Street, Brisbane QLD 4000", "phone": "+61 7 9999 0003"},
        {"name": "James Anderson", "address": "111 George Street, Brisbane QLD 4000", "phone": "+61 7 9999 0004"},
        {"name": "Mia Thompson", "address": "320 Adelaide Street, Brisbane QLD 4000", "phone": "+61 7 9999 0005"},
    ],
    "Adelaide": [
        {"name": "Lucas Harris", "address": "91 King William Street, Adelaide SA 5000", "phone": "+61 8 9999 0001"},
        {"name": "Charlotte Miller", "address": "45 Grenfell Street, Adelaide SA 5000", "phone": "+61 8 9999 0002"},
        {"name": "Henry Wilson", "address": "136 North Terrace, Adelaide SA 5000", "phone": "+61 8 9999 0003"},
    ]
}


async def generate_dispatcher_demo_parcels():
    """Generate unassigned parcels for dispatcher agent demo (today + tomorrow)"""
    
    print("="*70)
    print("📦 Generating Demo Parcels for Dispatcher Agent")
    print("="*70)
    
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        # Generate for today and tomorrow
        today = datetime.now(timezone.utc).date()
        tomorrow = today + timedelta(days=1)
        dates_to_generate = [
            (today, "Today"),
            (tomorrow, "Tomorrow")
        ]
        
        overall_total = 0
        
        for target_date, date_label in dates_to_generate:
            print(f"\n📅 Generating parcels for {date_label} ({target_date})")
            print("-" * 70)
            
            total_created = 0
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            
            # Generate parcels for each city
            parcel_distributions = {
                "Sydney": 20,
                "Melbourne": 15,
                "Brisbane": 10,
                "Adelaide": 5
            }
            
            for city, count in parcel_distributions.items():
                print(f"\n🏙️  {city}: Creating {count} parcels...")
                addresses = DEMO_ADDRESSES[city]
                
                for i in range(count):
                    # Cycle through addresses
                    addr = addresses[i % len(addresses)]
                    
                    # Generate unique barcode with timestamp and overall counter
                    barcode = f"DT{timestamp}{overall_total:04d}"
                    
                    # Extract state and postcode from address
                    address_parts = addr["address"].split()
                    state = None
                    postcode = None
                    
                    for j, part in enumerate(address_parts):
                        if part in ["NSW", "VIC", "QLD", "SA", "WA", "ACT"]:
                            state = part
                            if j + 1 < len(address_parts):
                                postcode = address_parts[j + 1]
                            break
                    
                    try:
                        # Register parcel first
                        parcel = await db.register_parcel(
                            barcode=barcode,
                            sender_name="DT Logistics Warehouse",
                            sender_address="123 Industrial Drive, Sydney NSW 2000",
                            sender_phone="+61 2 9999 0000",
                            recipient_name=f"{addr['name']} (Demo)",
                            recipient_address=addr["address"],
                            recipient_phone=addr["phone"],
                            destination_postcode=postcode or "0000",
                            destination_state=state or "NSW",
                            destination_city=city,
                            service_type="express" if i % 3 == 0 else "standard",
                            weight=round(0.5 + (i * 0.3), 2),
                            dimensions=f"{20+(i%30)}x{15+(i%25)}x{10+(i%20)}cm",
                            special_instructions="Demo parcel - please handle with care"
                        )
                        
                        # Update status to "at_depot" so AI auto-assign can find it (lowercase to match existing data)
                        await db.update_parcel_status(
                            barcode=barcode,
                            status="at_depot",
                            location="Central Distribution Centre",
                            scanned_by="system"
                        )
                        total_created += 1
                        overall_total += 1
                        
                    except Exception as e:
                        if "already exists" in str(e):
                            print(f"   ⚠️  Parcel {barcode} already exists")
                        else:
                            print(f"   ❌ Error creating parcel: {e}")
                
                print(f"   ✅ Created {count} parcels for {city}")
            
            print(f"   ✅ Total for {date_label}: {total_created} parcels")
        
        print(f"\n{'='*70}")
        print(f"✅ Successfully created {overall_total} total parcels!")
        print(f"   - Today: 50 parcels")
        print(f"   - Tomorrow: 50 parcels")
        print(f"   All parcels set to 'at_depot' status")
        print(f"{'='*70}")
        print(f"\n📊 Parcel Distribution (per day):")
        print(f"   Sydney:      20 parcels")
        print(f"   Melbourne:   15 parcels")
        print(f"   Brisbane:    10 parcels")
        print(f"   Adelaide:     5 parcels")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Navigate to: http://127.0.0.1:5000/admin/manifests")
        print(f"   2. Click 'AI Auto-Assign Parcels'")
        print(f"   3. Watch Dispatcher Agent assign parcels to drivers")
        print(f"\n💡 Tip: Run this script again between demos to replenish parcels")
        print("="*70)


if __name__ == "__main__":
    asyncio.run(generate_dispatcher_demo_parcels())
