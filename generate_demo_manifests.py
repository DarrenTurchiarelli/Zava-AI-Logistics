#!/usr/bin/env python3
"""
Generate sample driver manifests for demonstration
Creates realistic delivery data with Sydney addresses

:TODO When running use python and not py. Unsure why faker env is not picked up with py launcher
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from parcel_tracking_db import ParcelTrackingDB

load_dotenv()

# Sample Sydney addresses for demonstration
SAMPLE_ADDRESSES = [
    {
        "recipient": "Sarah Johnson",
        "address": "1 Macquarie Street, Sydney NSW 2000",
        "phone": "+61 2 9250 7111",
        "priority": "normal",
        "notes": "Office building - reception on ground floor"
    },
    {
        "recipient": "Michael Chen",
        "address": "88 Cumberland Street, The Rocks NSW 2000",
        "phone": "+61 2 9240 8500",
        "priority": "urgent",
        "notes": "Leave with concierge if not home"
    },
    {
        "recipient": "Emma Wilson",
        "address": "483 George Street, Sydney NSW 2000",
        "phone": "+61 2 9265 9000",
        "priority": "normal",
        "notes": "Call before delivery"
    },
    {
        "recipient": "James Martinez",
        "address": "201 Kent Street, Sydney NSW 2000",
        "phone": "+61 2 9320 6000",
        "priority": "normal",
        "notes": "Signature required"
    },
    {
        "recipient": "Olivia Brown",
        "address": "100 Market Street, Sydney NSW 2000",
        "phone": "+61 2 9267 3000",
        "priority": "urgent",
        "notes": "Fragile items - handle with care"
    },
    {
        "recipient": "William Taylor",
        "address": "456 Kent Street, Sydney NSW 2000",
        "phone": "+61 2 9286 3000",
        "priority": "normal",
        "notes": "Apartment 12B - use intercom"
    },
    {
        "recipient": "Sophia Anderson",
        "address": "200 Barangaroo Avenue, Barangaroo NSW 2000",
        "phone": "+61 2 8871 3000",
        "priority": "normal",
        "notes": "Security check required at entrance"
    },
    {
        "recipient": "Benjamin Lee",
        "address": "1 Bligh Street, Sydney NSW 2000",
        "phone": "+61 2 8223 0000",
        "priority": "urgent",
        "notes": "Time-sensitive delivery"
    },
    {
        "recipient": "Charlotte Harris",
        "address": "680 George Street, Sydney NSW 2000",
        "phone": "+61 2 9265 8888",
        "priority": "normal",
        "notes": "Leave at front desk"
    },
    {
        "recipient": "Daniel Kim",
        "address": "1 O'Connell Street, Sydney NSW 2000",
        "phone": "+61 2 8247 7000",
        "priority": "normal",
        "notes": "Ring doorbell twice"
    },
    {
        "recipient": "Amelia White",
        "address": "111 Harrington Street, The Rocks NSW 2000",
        "phone": "+61 2 9252 0524",
        "priority": "normal",
        "notes": "Historic building - use main entrance"
    },
    {
        "recipient": "Lucas Thompson",
        "address": "52 Martin Place, Sydney NSW 2000",
        "phone": "+61 2 9551 8911",
        "priority": "urgent",
        "notes": "Perishable goods - priority delivery"
    },
    {
        "recipient": "Mia Garcia",
        "address": "135 King Street, Sydney NSW 2000",
        "phone": "+61 2 9231 9700",
        "priority": "normal",
        "notes": "Commercial property - business hours only"
    },
    {
        "recipient": "Ethan Rodriguez",
        "address": "388 George Street, Sydney NSW 2000",
        "phone": "+61 2 9265 8888",
        "priority": "normal",
        "notes": "Leave with building manager"
    },
    {
        "recipient": "Isabella Martinez",
        "address": "181 Miller Street, North Sydney NSW 2060",
        "phone": "+61 2 9922 1211",
        "priority": "normal",
        "notes": "Cross harbour bridge for delivery"
    },
    {
        "recipient": "Mason Davis",
        "address": "1 Denison Street, North Sydney NSW 2060",
        "phone": "+61 2 9922 8888",
        "priority": "urgent",
        "notes": "Medical supplies - handle carefully"
    },
    {
        "recipient": "Harper Wilson",
        "address": "33 Saunders Street, Pyrmont NSW 2009",
        "phone": "+61 2 9692 0222",
        "priority": "normal",
        "notes": "Waterfront apartment - parking in visitor bay"
    },
    {
        "recipient": "Alexander Moore",
        "address": "35 Clarence Street, Sydney NSW 2000",
        "phone": "+61 2 9241 1888",
        "priority": "normal",
        "notes": "Requires ID verification"
    },
    {
        "recipient": "Evelyn Jackson",
        "address": "70 Castlereagh Street, Sydney NSW 2000",
        "phone": "+61 2 9265 6000",
        "priority": "normal",
        "notes": "Department store - deliver to loading dock"
    },
    {
        "recipient": "Sebastian Clark",
        "address": "225 George Street, Sydney NSW 2000",
        "phone": "+61 2 9240 1234",
        "priority": "urgent",
        "notes": "Electronics - do not leave unattended"
    }
]

# Sample drivers
SAMPLE_DRIVERS = [
    {"id": "driver-001", "name": "John Smith"},
    {"id": "driver-002", "name": "Maria Garcia"},
    {"id": "driver-003", "name": "David Wong"},
]

async def create_sample_parcels(db: ParcelTrackingDB):
    """Create sample parcels in the database"""
    
    print("Creating sample parcels...")
    barcodes = []
    
    for i, addr_info in enumerate(SAMPLE_ADDRESSES, 1):
        barcode = f"DT{datetime.now().strftime('%Y%m%d')}{i:04d}"
        
        # Extract postcode and state from address
        address_parts = addr_info["address"].split(",")
        state_postcode = address_parts[-1].strip() if len(address_parts) > 0 else "NSW 2000"
        state = state_postcode.split()[0] if state_postcode else "NSW"
        postcode = state_postcode.split()[1] if len(state_postcode.split()) > 1 else "2000"
        
        try:
            await db.register_parcel(
                barcode=barcode,
                sender_name="DT Logistics Warehouse",
                sender_address="123 Industrial Drive, Sydney NSW 2000",
                sender_phone="+61 2 9999 0000",
                recipient_name=addr_info["recipient"],
                recipient_address=addr_info["address"],
                recipient_phone=addr_info["phone"],
                destination_postcode=postcode,
                destination_state=state,
                service_type=addr_info["priority"],
                weight=round(0.5 + (i * 0.3), 2),
                dimensions=f"{20+i}x{15+i}x{10+i}cm",
                special_instructions=addr_info["notes"]
            )
            barcodes.append(barcode)
            print(f"   ✅ Created parcel {barcode} for {addr_info['recipient']}")
        except Exception as e:
            if "already exists" in str(e):
                barcodes.append(barcode)
                print(f"   ⚠️  Parcel {barcode} already exists - reusing")
            else:
                print(f"   ❌ Error creating parcel {barcode}: {e}")
    
    return barcodes

async def create_driver_manifests(db: ParcelTrackingDB, all_barcodes: list):
    """Create manifests for sample drivers"""
    
    print("\n🚚 Creating driver manifests...")
    
    # Distribute parcels among drivers
    parcels_per_driver = len(all_barcodes) // len(SAMPLE_DRIVERS)
    
    for i, driver in enumerate(SAMPLE_DRIVERS):
        # Get subset of parcels for this driver
        start_idx = i * parcels_per_driver
        end_idx = start_idx + parcels_per_driver if i < len(SAMPLE_DRIVERS) - 1 else len(all_barcodes)
        driver_barcodes = all_barcodes[start_idx:end_idx]
        
        if not driver_barcodes:
            continue
        
        print(f"\n   Driver: {driver['name']} ({driver['id']})")
        print(f"   Parcels: {len(driver_barcodes)}")
        
        try:
            manifest_id = await db.create_driver_manifest(
                driver_id=driver['id'],
                driver_name=driver['name'],
                parcel_barcodes=driver_barcodes
            )
            
            if manifest_id:
                # Fetch the created manifest to display details
                manifest = await db.get_driver_manifest(driver['id'])
                
                print(f"   ✅ Manifest created: {manifest_id}")
                if manifest:
                    print(f"      - Total items: {manifest['total_items']}")
                    print(f"      - Status: {manifest['status']}")
                    
                    # Display first 3 addresses
                    print(f"      - Sample deliveries:")
                    for item in manifest['items'][:3]:
                        print(f"        • {item['recipient_name']} - {item['recipient_address']}")
                    
                    if len(manifest['items']) > 3:
                        print(f"        ... and {len(manifest['items']) - 3} more")
            else:
                print(f"   ❌ Failed to create manifest")
                
        except Exception as e:
            print(f"   ❌ Error creating manifest: {e}")

async def main():
    """Main demonstration setup"""
    
    print("=" * 70)
    print("Driver Manifest Demo Data Generator")
    print("=" * 70)
    print()
    
    from depot_manager import get_depot_manager
    depot_mgr = get_depot_manager()
    
    print("Configured Depots:")
    for state, depot_address in depot_mgr.list_depots().items():
        print(f"   {state}: {depot_address}")
    
    depot = depot_mgr.get_default_depot()
    print(f"\nDefault Depot: {depot}")
    print(f"Date: {datetime.now().strftime('%A, %B %d, %Y')}")
    print()
    
    async with ParcelTrackingDB() as db:
        # Create sample parcels
        barcodes = await create_sample_parcels(db)
        
        if not barcodes:
            print("\n❌ No parcels were created. Cannot generate manifests.")
            return
        
        print(f"\n✅ Created {len(barcodes)} sample parcels")
        
        # Create driver manifests
        await create_driver_manifests(db, barcodes)
    
    print("\n" + "=" * 70)
    print("✅ Demo Data Generation Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Open your browser to http://127.0.0.1:5000")
    print("2. Navigate to 'Drivers > Manage Manifests' to see all manifests")
    print("3. Navigate to 'Drivers > My Manifest' to see individual driver views")
    print("4. Sample drivers you can use:")
    for driver in SAMPLE_DRIVERS:
        print(f"   - {driver['name']}: {driver['id']}")
    print()
    print("💡 Tip: Add AZURE_MAPS_SUBSCRIPTION_KEY to .env for route optimization")
    print()

if __name__ == "__main__":
    asyncio.run(main())
