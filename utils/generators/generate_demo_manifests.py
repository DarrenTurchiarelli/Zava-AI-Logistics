#!/usr/bin/env python3
"""
Generate sample driver manifests for demonstration
Creates realistic delivery data with Sydney addresses

:TODO When running use python and not py. Unsure why faker env is not picked up with py launcher
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path to find parcel_tracking_db
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

# Sample drivers - expanded to 57 drivers
SAMPLE_DRIVERS = [
    {"id": "driver-001", "name": "John Smith"},
    {"id": "driver-002", "name": "Maria Garcia"},
    {"id": "driver-003", "name": "David Wong"},
    {"id": "driver-004", "name": "Emily Thompson"},
    {"id": "driver-005", "name": "Robert Kumar"},
    {"id": "driver-006", "name": "Jessica O'Brien"},
    {"id": "driver-007", "name": "Michael Nguyen"},
    {"id": "driver-008", "name": "Sarah Mitchell"},
    {"id": "driver-009", "name": "Christopher Lee"},
    {"id": "driver-010", "name": "Amanda Roberts"},
    {"id": "driver-011", "name": "Daniel Foster"},
    {"id": "driver-012", "name": "Rachel Hughes"},
    {"id": "driver-013", "name": "Matthew Singh"},
    {"id": "driver-014", "name": "Lauren Edwards"},
    {"id": "driver-015", "name": "Andrew Campbell"},
    {"id": "driver-016", "name": "Nicole Zhang"},
    {"id": "driver-017", "name": "Patrick Walsh"},
    {"id": "driver-018", "name": "Victoria Chen"},
    {"id": "driver-019", "name": "Thomas Anderson"},
    {"id": "driver-020", "name": "Sophia Martinez"},
    {"id": "driver-021", "name": "James Wilson"},
    {"id": "driver-022", "name": "Isabella Taylor"},
    {"id": "driver-023", "name": "Benjamin Moore"},
    {"id": "driver-024", "name": "Mia Jackson"},
    {"id": "driver-025", "name": "Lucas Martin"},
    {"id": "driver-026", "name": "Charlotte Lee"},
    {"id": "driver-027", "name": "Mason Harris"},
    {"id": "driver-028", "name": "Amelia Clark"},
    {"id": "driver-029", "name": "Ethan Lewis"},
    {"id": "driver-030", "name": "Harper Walker"},
    {"id": "driver-031", "name": "Alexander Young"},
    {"id": "driver-032", "name": "Evelyn Hall"},
    {"id": "driver-033", "name": "Daniel Allen"},
    {"id": "driver-034", "name": "Abigail King"},
    {"id": "driver-035", "name": "Matthew Wright"},
    {"id": "driver-036", "name": "Emily Scott"},
    {"id": "driver-037", "name": "Joseph Green"},
    {"id": "driver-038", "name": "Elizabeth Adams"},
    {"id": "driver-039", "name": "David Baker"},
    {"id": "driver-040", "name": "Sofia Nelson"},
    {"id": "driver-041", "name": "Samuel Carter"},
    {"id": "driver-042", "name": "Avery Mitchell"},
    {"id": "driver-043", "name": "Henry Perez"},
    {"id": "driver-044", "name": "Scarlett Roberts"},
    {"id": "driver-045", "name": "Sebastian Turner"},
    {"id": "driver-046", "name": "Grace Phillips"},
    {"id": "driver-047", "name": "Jack Campbell"},
    {"id": "driver-048", "name": "Chloe Parker"},
    {"id": "driver-049", "name": "Owen Evans"},
    {"id": "driver-050", "name": "Lily Edwards"},
    {"id": "driver-051", "name": "Ryan Collins"},
    {"id": "driver-052", "name": "Zoe Stewart"},
    {"id": "driver-053", "name": "Nathan Sanchez"},
    {"id": "driver-054", "name": "Hannah Morris"},
    {"id": "driver-055", "name": "Caleb Rogers"},
    {"id": "driver-056", "name": "Aria Reed"},
    {"id": "driver-057", "name": "Isaac Cook"},
]

async def create_sample_parcels(db: ParcelTrackingDB, num_parcels: int = 2500):
    """Create sample parcels in the database
    
    Args:
        num_parcels: Number of parcels to create (default 2500 for 57 drivers × ~44 parcels)
    """
    
    print(f"Creating {num_parcels} sample parcels...")
    barcodes = []
    
    # Cycle through sample addresses to generate more parcels
    for i in range(1, num_parcels + 1):
        barcode = f"DT{datetime.now().strftime('%Y%m%d')}{i:04d}"
        
        # Cycle through sample addresses
        addr_info = SAMPLE_ADDRESSES[(i - 1) % len(SAMPLE_ADDRESSES)]
        
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
                recipient_name=f"{addr_info['recipient']} #{i}",  # Add number to make unique
                recipient_address=addr_info["address"],
                recipient_phone=addr_info["phone"],
                destination_postcode=postcode,
                destination_state=state,
                service_type=addr_info["priority"],
                weight=round(0.5 + ((i % 50) * 0.3), 2),
                dimensions=f"{20+(i%30)}x{15+(i%25)}x{10+(i%20)}cm",
                special_instructions=addr_info["notes"]
            )
            barcodes.append(barcode)
            
            # Progress indicator
            if i % 50 == 0:
                print(f"   Created {i}/{num_parcels} parcels...")
        except Exception as e:
            if "already exists" in str(e):
                barcodes.append(barcode)
                if i <= 20:  # Only show first few reuse messages
                    print(f"   ⚠️  Parcel {barcode} already exists - reusing")
            else:
                print(f"   ❌ Error creating parcel {barcode}: {e}")
    
    print(f"   ✅ Total parcels ready: {len(barcodes)}")
    return barcodes

async def delete_all_manifests(db: ParcelTrackingDB):
    """Delete all existing driver manifests"""
    
    print("\n🗑️  Deleting existing manifests...")
    
    try:
        container = db.database.get_container_client("driver_manifests")
        
        # Query all manifests - remove the problematic parameter
        query = "SELECT c.id, c.driver_id FROM c"
        manifests_to_delete = []
        
        # Use query_items without enable_cross_partition_query parameter
        # The SDK handles cross-partition queries automatically
        query_iterable = container.query_items(query=query)
        
        async for item in query_iterable:
            manifests_to_delete.append({
                'id': item['id'],
                'driver_id': item['driver_id']
            })
        
        print(f"   Found {len(manifests_to_delete)} manifests to delete")
        
        # Delete each manifest using correct partition key
        deleted_count = 0
        for manifest in manifests_to_delete:
            try:
                # Use driver_id as partition key (as per create_driver_manifest)
                await container.delete_item(
                    item=manifest['id'], 
                    partition_key=manifest['driver_id']
                )
                deleted_count += 1
                if deleted_count % 10 == 0:
                    print(f"   Deleted {deleted_count}/{len(manifests_to_delete)} manifests...")
            except Exception as e:
                print(f"   ⚠️  Error deleting {manifest['id']}: {e}")
        
        print(f"   ✅ Deleted {deleted_count} manifests")
        return deleted_count
        
    except Exception as e:
        print(f"   ❌ Error deleting manifests: {e}")
        import traceback
        traceback.print_exc()
        return 0

async def create_driver_manifests(db: ParcelTrackingDB, all_barcodes: list):
    """Create manifests for sample drivers with varied parcel counts (30-50 each)"""
    
    import random
    from datetime import datetime
    
    print(f"\n🚚 Creating driver manifests for {len(SAMPLE_DRIVERS)} drivers...")
    print(f"   Total parcels available: {len(all_barcodes)}")
    
    # Shuffle barcodes for random distribution
    shuffled_barcodes = all_barcodes.copy()
    random.shuffle(shuffled_barcodes)
    
    # Distribute parcels with variation (30-50 per driver)
    current_idx = 0
    manifests_created = 0
    
    for driver in SAMPLE_DRIVERS:
        # Random number of parcels between 30 and 50
        num_parcels = random.randint(30, 50)
        
        # Get parcels for this driver
        driver_barcodes = shuffled_barcodes[current_idx:current_idx + num_parcels]
        current_idx += num_parcels
        
        if not driver_barcodes:
            print(f"   ⚠️  No more parcels available for {driver['name']}")
            continue
        
        print(f"\n   Driver: {driver['name']} ({driver['id']}) - {len(driver_barcodes)} parcels")
        
        try:
            manifest_id = await db.create_driver_manifest(
                driver_id=driver['id'],
                driver_name=driver['name'],
                parcel_barcodes=driver_barcodes
            )
            
            if manifest_id:
                manifests_created += 1
                # Fetch the created manifest to display details
                manifest = await db.get_driver_manifest(driver['id'])
                
                print(f"      ✅ Manifest: {manifest_id}")
                if manifest:
                    print(f"         Total items: {manifest['total_items']}")
                    print(f"         Status: {manifest['status']}")
                    
                    # Display first 2 addresses
                    for item in manifest['items'][:2]:
                        print(f"         • {item['recipient_name']} - {item['recipient_address'][:50]}...")
                    
                    if len(manifest['items']) > 2:
                        print(f"         ... and {len(manifest['items']) - 2} more")
            else:
                print(f"      ❌ Failed to create manifest")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    print(f"\n   📊 Summary:")
    print(f"      Created: {manifests_created} manifests")
    print(f"      Total drivers: {len(SAMPLE_DRIVERS)}")
    print(f"   📦 Parcels distributed: {current_idx}/{len(all_barcodes)}")

async def main():
    """Main demonstration setup"""
    
    print("=" * 70)
    print("Driver Manifest Demo Data Generator")
    print("=" * 70)
    print()
    
    from config.depots import get_depot_manager
    depot_mgr = get_depot_manager()
    
    print("Configured Depots:")
    for state, depot_address in depot_mgr.list_depots().items():
        print(f"   {state}: {depot_address}")
    
    depot = depot_mgr.get_default_depot()
    print(f"\nDefault Depot: {depot}")
    print(f"Date: {datetime.now().strftime('%A, %B %d, %Y')}")
    print()
    
    async with ParcelTrackingDB() as db:
        # Delete existing manifests
        await delete_all_manifests(db)
        
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
    print(f"Generated:")
    print(f"   • {len(barcodes)} parcels")
    print(f"   • {len(SAMPLE_DRIVERS)} driver manifests")
    print(f"   • 30-50 parcels per driver (randomized)")
    print()
    print("Next steps:")
    print("1. Open your browser to http://127.0.0.1:5000")
    print("2. Navigate to 'Admin > View Manifests' to see all manifests")
    print("3. Navigate to 'Drivers > My Manifest' to see individual driver views")
    print()
    print("Sample drivers (first 5):")
    for driver in SAMPLE_DRIVERS[:5]:
        print(f"   - {driver['name']}: {driver['id']}")
    print(f"   ... and {len(SAMPLE_DRIVERS) - 5} more drivers")
    print()
    print("💡 Tip: Add AZURE_MAPS_SUBSCRIPTION_KEY to .env for route optimization")
    print()

if __name__ == "__main__":
    asyncio.run(main())
