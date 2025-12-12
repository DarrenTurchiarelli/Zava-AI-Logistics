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

# Additional addresses for other Australian states
SAMPLE_ADDRESSES_VIC = [
    {"recipient": "Oliver Thompson", "address": "120 Collins Street, Melbourne VIC 3000", "phone": "+61 3 9654 1234", "priority": "normal", "notes": "CBD office building"},
    {"recipient": "Emma Wilson", "address": "1 Flinders Street, Melbourne VIC 3000", "phone": "+61 3 9619 5000", "priority": "normal", "notes": "Near Flinders Street Station"},
    {"recipient": "Noah Brown", "address": "8 Exhibition Street, Melbourne VIC 3000", "phone": "+61 3 9639 8888", "priority": "urgent", "notes": "Parliament precinct"},
    {"recipient": "Sophia Martin", "address": "501 Swanston Street, Melbourne VIC 3000", "phone": "+61 3 9347 2000", "priority": "normal", "notes": "University area"},
    {"recipient": "Liam Davis", "address": "181 William Street, Melbourne VIC 3000", "phone": "+61 3 9320 5000", "priority": "normal", "notes": "Legal district"},
]

SAMPLE_ADDRESSES_QLD = [
    {"recipient": "Ava Johnson", "address": "100 Queen Street, Brisbane QLD 4000", "phone": "+61 7 3229 9111", "priority": "normal", "notes": "Brisbane CBD"},
    {"recipient": "William Taylor", "address": "12 Creek Street, Brisbane QLD 4000", "phone": "+61 7 3221 6111", "priority": "urgent", "notes": "Financial district"},
    {"recipient": "Isabella White", "address": "45 Eagle Street, Brisbane QLD 4000", "phone": "+61 7 3221 2333", "priority": "normal", "notes": "Riverside area"},
    {"recipient": "James Anderson", "address": "111 George Street, Brisbane QLD 4000", "phone": "+61 7 3229 8111", "priority": "normal", "notes": "Treasury building area"},
    {"recipient": "Mia Thompson", "address": "320 Adelaide Street, Brisbane QLD 4000", "phone": "+61 7 3222 1234", "priority": "normal", "notes": "Central Brisbane"},
]

SAMPLE_ADDRESSES_SA = [
    {"recipient": "Lucas Harris", "address": "91 King William Street, Adelaide SA 5000", "phone": "+61 8 8223 1234", "priority": "normal", "notes": "Adelaide CBD"},
    {"recipient": "Charlotte Miller", "address": "45 Grenfell Street, Adelaide SA 5000", "phone": "+61 8 8212 3456", "priority": "normal", "notes": "City center"},
    {"recipient": "Henry Wilson", "address": "136 North Terrace, Adelaide SA 5000", "phone": "+61 8 8207 1234", "priority": "urgent", "notes": "Cultural precinct"},
    {"recipient": "Amelia Jones", "address": "25 Pirie Street, Adelaide SA 5000", "phone": "+61 8 8223 5678", "priority": "normal", "notes": "Retail district"},
]

SAMPLE_ADDRESSES_WA = [
    {"recipient": "Benjamin Clark", "address": "125 St Georges Terrace, Perth WA 6000", "phone": "+61 8 9220 1234", "priority": "normal", "notes": "Perth CBD"},
    {"recipient": "Harper Lewis", "address": "200 Murray Street, Perth WA 6000", "phone": "+61 8 9321 5678", "priority": "normal", "notes": "City center"},
    {"recipient": "Ethan Walker", "address": "108 Hay Street, Perth WA 6000", "phone": "+61 8 9321 8888", "priority": "urgent", "notes": "Shopping district"},
]

SAMPLE_ADDRESSES_ACT = [
    {"recipient": "Olivia Robinson", "address": "1 Constitution Avenue, Canberra ACT 2600", "phone": "+61 2 6270 1234", "priority": "urgent", "notes": "Government precinct"},
    {"recipient": "Alexander King", "address": "45 Northbourne Avenue, Canberra ACT 2600", "phone": "+61 2 6248 5678", "priority": "normal", "notes": "Civic area"},
]

# Sample drivers - 57 drivers distributed across Australian states
# NSW: 25 drivers, VIC: 12 drivers, QLD: 10 drivers, SA: 6 drivers, WA: 3 drivers, ACT: 1 driver
SAMPLE_DRIVERS = [
    # NSW Drivers (25)
    {"id": "driver-001", "name": "John Smith", "state": "NSW"},
    {"id": "driver-002", "name": "Maria Garcia", "state": "NSW"},
    {"id": "driver-003", "name": "David Wong", "state": "NSW"},
    {"id": "driver-004", "name": "Emily Thompson", "state": "NSW"},
    {"id": "driver-005", "name": "Robert Kumar", "state": "NSW"},
    {"id": "driver-006", "name": "Jessica O'Brien", "state": "NSW"},
    {"id": "driver-007", "name": "Michael Nguyen", "state": "NSW"},
    {"id": "driver-008", "name": "Sarah Mitchell", "state": "NSW"},
    {"id": "driver-009", "name": "Christopher Lee", "state": "NSW"},
    {"id": "driver-010", "name": "Amanda Roberts", "state": "NSW"},
    {"id": "driver-011", "name": "Daniel Foster", "state": "NSW"},
    {"id": "driver-012", "name": "Rachel Hughes", "state": "NSW"},
    {"id": "driver-013", "name": "Matthew Singh", "state": "NSW"},
    {"id": "driver-014", "name": "Lauren Edwards", "state": "NSW"},
    {"id": "driver-015", "name": "Andrew Campbell", "state": "NSW"},
    {"id": "driver-016", "name": "Nicole Zhang", "state": "NSW"},
    {"id": "driver-017", "name": "Patrick Walsh", "state": "NSW"},
    {"id": "driver-018", "name": "Victoria Chen", "state": "NSW"},
    {"id": "driver-019", "name": "Thomas Anderson", "state": "NSW"},
    {"id": "driver-020", "name": "Sophia Martinez", "state": "NSW"},
    {"id": "driver-021", "name": "James Wilson", "state": "NSW"},
    {"id": "driver-022", "name": "Isabella Taylor", "state": "NSW"},
    {"id": "driver-023", "name": "Benjamin Moore", "state": "NSW"},
    {"id": "driver-024", "name": "Mia Jackson", "state": "NSW"},
    {"id": "driver-025", "name": "Lucas Martin", "state": "NSW"},
    
    # VIC Drivers (12)
    {"id": "driver-026", "name": "Charlotte Lee", "state": "VIC"},
    {"id": "driver-027", "name": "Mason Harris", "state": "VIC"},
    {"id": "driver-028", "name": "Amelia Clark", "state": "VIC"},
    {"id": "driver-029", "name": "Ethan Lewis", "state": "VIC"},
    {"id": "driver-030", "name": "Harper Walker", "state": "VIC"},
    {"id": "driver-031", "name": "Alexander Young", "state": "VIC"},
    {"id": "driver-032", "name": "Evelyn Hall", "state": "VIC"},
    {"id": "driver-033", "name": "Daniel Allen", "state": "VIC"},
    {"id": "driver-034", "name": "Abigail King", "state": "VIC"},
    {"id": "driver-035", "name": "Matthew Wright", "state": "VIC"},
    {"id": "driver-036", "name": "Emily Scott", "state": "VIC"},
    {"id": "driver-037", "name": "Joseph Green", "state": "VIC"},
    
    # QLD Drivers (10)
    {"id": "driver-038", "name": "Elizabeth Adams", "state": "QLD"},
    {"id": "driver-039", "name": "David Baker", "state": "QLD"},
    {"id": "driver-040", "name": "Sofia Nelson", "state": "QLD"},
    {"id": "driver-041", "name": "Samuel Carter", "state": "QLD"},
    {"id": "driver-042", "name": "Avery Mitchell", "state": "QLD"},
    {"id": "driver-043", "name": "Henry Perez", "state": "QLD"},
    {"id": "driver-044", "name": "Scarlett Roberts", "state": "QLD"},
    {"id": "driver-045", "name": "Sebastian Turner", "state": "QLD"},
    {"id": "driver-046", "name": "Grace Phillips", "state": "QLD"},
    {"id": "driver-047", "name": "Jack Campbell", "state": "QLD"},
    
    # SA Drivers (6)
    {"id": "driver-048", "name": "Chloe Parker", "state": "SA"},
    {"id": "driver-049", "name": "Owen Evans", "state": "SA"},
    {"id": "driver-050", "name": "Lily Edwards", "state": "SA"},
    {"id": "driver-051", "name": "Ryan Collins", "state": "SA"},
    {"id": "driver-052", "name": "Zoe Stewart", "state": "SA"},
    {"id": "driver-053", "name": "Nathan Sanchez", "state": "SA"},
    
    # WA Drivers (3)
    {"id": "driver-054", "name": "Hannah Morris", "state": "WA"},
    {"id": "driver-055", "name": "Caleb Rogers", "state": "WA"},
    {"id": "driver-056", "name": "Aria Reed", "state": "WA"},
    
    # ACT Driver (1)
    {"id": "driver-057", "name": "Isaac Cook", "state": "ACT"},
]

# Map states to their address pools
STATE_ADDRESS_POOLS = {
    "NSW": SAMPLE_ADDRESSES,
    "VIC": SAMPLE_ADDRESSES_VIC,
    "QLD": SAMPLE_ADDRESSES_QLD,
    "SA": SAMPLE_ADDRESSES_SA,
    "WA": SAMPLE_ADDRESSES_WA,
    "ACT": SAMPLE_ADDRESSES_ACT,
}

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
                sender_address="1 Homebush Bay Drive, Rhodes NSW 2138",
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

async def create_sample_parcels_by_state(db: ParcelTrackingDB):
    """Create sample parcels distributed across different Australian states
    
    Returns:
        Dictionary mapping state codes to lists of barcodes
    """
    from config.depots import get_depot_manager
    depot_mgr = get_depot_manager()
    
    print(f"Creating parcels across Australian states...")
    state_barcodes = {state: [] for state in STATE_ADDRESS_POOLS.keys()}
    
    # Calculate parcels per state based on number of drivers
    state_driver_counts = {}
    for driver in SAMPLE_DRIVERS:
        state = driver.get('state', 'NSW')
        state_driver_counts[state] = state_driver_counts.get(state, 0) + 1
    
    parcel_counter = 1
    
    for state, address_pool in STATE_ADDRESS_POOLS.items():
        num_drivers = state_driver_counts.get(state, 0)
        if num_drivers == 0:
            continue
            
        # ~40 parcels per driver average
        num_parcels = num_drivers * 40
        
        # Get depot for this state
        depot_address = depot_mgr.get_depot(state) or depot_mgr.get_default_depot()
        
        print(f"\n   {state}: Creating {num_parcels} parcels for {num_drivers} drivers")
        print(f"      Depot: {depot_address}")
        
        for i in range(num_parcels):
            barcode = f"DT{datetime.now().strftime('%Y%m%d')}{parcel_counter:04d}"
            parcel_counter += 1
            
            # Cycle through addresses for this state
            addr_info = address_pool[i % len(address_pool)]
            
            # Extract postcode and state from address
            address_parts = addr_info["address"].split(",")
            state_postcode = address_parts[-1].strip()
            actual_state = state_postcode.split()[0] if state_postcode else state
            postcode = state_postcode.split()[1] if len(state_postcode.split()) > 1 else "0000"
            
            try:
                await db.register_parcel(
                    barcode=barcode,
                    sender_name="DT Logistics Warehouse",
                    sender_address=depot_address,
                    sender_phone="+61 2 9999 0000",
                    recipient_name=f"{addr_info['recipient']} #{parcel_counter}",
                    recipient_address=addr_info["address"],
                    recipient_phone=addr_info["phone"],
                    destination_postcode=postcode,
                    destination_state=actual_state,
                    service_type=addr_info["priority"],
                    weight=round(0.5 + ((parcel_counter % 50) * 0.3), 2),
                    dimensions=f"{20+(parcel_counter%30)}x{15+(parcel_counter%25)}x{10+(parcel_counter%20)}cm",
                    special_instructions=addr_info["notes"]
                )
                state_barcodes[state].append(barcode)
            except Exception as e:
                if "already exists" in str(e):
                    state_barcodes[state].append(barcode)
                else:
                    print(f"      ❌ Error creating parcel {barcode}: {e}")
        
        print(f"      ✅ Created {len(state_barcodes[state])} parcels for {state}")
    
    return state_barcodes

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

async def create_driver_manifests(db: ParcelTrackingDB, state_barcodes: dict):
    """Create manifests for sample drivers with varied parcel counts (30-50 each)
    
    Args:
        state_barcodes: Dictionary mapping state codes to lists of barcodes
    """
    
    import random
    from datetime import datetime
    
    print(f"\n🚚 Creating driver manifests for {len(SAMPLE_DRIVERS)} drivers across states...")
    
    # Distribute parcels with variation (30-50 per driver)
    manifests_created = 0
    
    for driver in SAMPLE_DRIVERS:
        driver_state = driver.get('state', 'NSW')
        
        # Get available barcodes for this driver's state
        available_barcodes = state_barcodes.get(driver_state, [])
        
        if not available_barcodes:
            print(f"\n   ⚠️  No parcels available for {driver['name']} in {driver_state}")
            continue
        
        # Random number of parcels between 30 and 50
        num_parcels = min(random.randint(30, 50), len(available_barcodes))
        
        # Get parcels for this driver and remove from pool
        driver_barcodes = available_barcodes[:num_parcels]
        state_barcodes[driver_state] = available_barcodes[num_parcels:]
        
        print(f"\n   Driver: {driver['name']} ({driver['id']}) [{driver_state}] - {len(driver_barcodes)} parcels")
        
        try:
            manifest_id = await db.create_driver_manifest(
                driver_id=driver['id'],
                driver_name=driver['name'],
                parcel_barcodes=driver_barcodes,
                driver_state=driver_state
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
    
    # Calculate total parcels distributed
    total_distributed = len(SAMPLE_DRIVERS) * 40  # approximate
    
    print(f"\n   📊 Summary:")
    print(f"      Created: {manifests_created} manifests")
    print(f"      Total drivers: {len(SAMPLE_DRIVERS)}")
    
    # Show breakdown by state
    state_counts = {}
    for driver in SAMPLE_DRIVERS:
        state = driver.get('state', 'NSW')
        state_counts[state] = state_counts.get(state, 0) + 1
    
    print(f"\n   🗺️  Distribution by state:")
    for state, count in sorted(state_counts.items()):
        print(f"      {state}: {count} drivers")

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
        
        # Create sample parcels by state
        state_barcodes = await create_sample_parcels_by_state(db)
        
        total_parcels = sum(len(barcodes) for barcodes in state_barcodes.values())
        if total_parcels == 0:
            print("\n❌ No parcels were created. Cannot generate manifests.")
            return
        
        print(f"\n✅ Created {total_parcels} sample parcels across {len(state_barcodes)} states")
        
        # Create driver manifests
        await create_driver_manifests(db, state_barcodes)
    
    print("\n" + "=" * 70)
    print("✅ Demo Data Generation Complete!")
    print("=" * 70)
    print()
    print(f"Generated:")
    print(f"   • {total_parcels} parcels")
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
