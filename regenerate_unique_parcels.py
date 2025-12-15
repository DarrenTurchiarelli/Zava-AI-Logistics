"""Generate 500 unique parcels + 100 duplicate addresses for realistic delivery scenarios"""
import asyncio
import random
from datetime import datetime
from faker import Faker
from parcel_tracking_db import ParcelTrackingDB

# Initialize Faker for Australian addresses
fake = Faker('en_AU')

async def regenerate_driver_parcels():
    """Generate 500 unique addresses + 100 duplicates, then create driver manifests"""
    
    async with ParcelTrackingDB() as db:
        print("\n" + "="*80)
        print("🔄 GENERATING 600 PARCELS (500 UNIQUE + 100 DUPLICATE ADDRESSES)")
        print("="*80)
        
        # Delete existing manifests for all drivers
        manifest_container = db.database.get_container_client('driver_manifests')
        query = 'SELECT * FROM c WHERE STARTSWITH(c.driver_id, "driver-")'
        
        deleted_manifests = 0
        async for manifest in manifest_container.query_items(query=query):
            await manifest_container.delete_item(item=manifest['id'], partition_key=manifest['driver_id'])
            deleted_manifests += 1
        
        print(f"   Deleted {deleted_manifests} existing manifests")
        
        # Delete old parcels (from DT20251215 onwards)
        parcels_container = db.database.get_container_client('parcels')
        query = "SELECT * FROM c WHERE STARTSWITH(c.barcode, 'DT20251215')"
        
        deleted_count = 0
        async for parcel in parcels_container.query_items(query=query):
            try:
                await parcels_container.delete_item(item=parcel['id'], partition_key=parcel['barcode'])
                deleted_count += 1
            except Exception:
                pass  # Already deleted or doesn't exist
        
        print(f"   Deleted {deleted_count} old parcels")
        
        print(f"\n📍 STEP 1: Generating 500 unique Sydney addresses...")
        
        # Generate 500 unique Sydney addresses using Faker
        unique_addresses = []
        unique_recipients = []
        used_addresses = set()
        
        sydney_postcodes = ['2000', '2007', '2008', '2009', '2010', '2021', '2026', '2028', 
                           '2037', '2040', '2042', '2048', '2060', '2061', '2065', '2088']
        
        while len(unique_addresses) < 500:
            street_address = fake.street_address()
            suburb = fake.city()
            postcode = random.choice(sydney_postcodes)
            address = f"{street_address}, {suburb} NSW {postcode}"
            
            # Ensure uniqueness
            if address not in used_addresses:
                used_addresses.add(address)
                unique_addresses.append(address)
                unique_recipients.append(fake.name())
        
        print(f"   ✅ Generated {len(unique_addresses)} unique addresses")
        
        print(f"\n📦 STEP 2: Creating 500 parcels with unique addresses...")
        
        parcel_counter = 1
        all_parcels = []  # Store all parcel info for later manifest creation
        
        # Prepare all parcels first (in-memory, fast)
        parcels_to_create = []
        for i in range(500):
            barcode = f"DT{datetime.now().strftime('%Y%m%d')}{parcel_counter:04d}"
            parcel_counter += 1
            
            address = unique_addresses[i]
            recipient = unique_recipients[i]
            phone = f"+61 4{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"
            priority = random.choice(['normal', 'normal', 'normal', 'urgent'])
            
            parcels_to_create.append({
                'barcode': barcode,
                'sender_name': "DT Logistics Warehouse",
                'sender_address': "1 Homebush Bay Drive, Rhodes NSW 2138",
                'sender_phone': "+61 2 9999 0000",
                'recipient_name': recipient,
                'recipient_address': address,
                'recipient_phone': phone,
                'destination_postcode': address.split()[-1],
                'destination_state': "NSW",
                'service_type': priority,
                'special_instructions': random.choice([
                    "Leave with reception",
                    "Call before delivery",
                    "Signature required",
                    "Leave at front door",
                    "Ring doorbell twice",
                    "Contact on arrival"
                ])
            })
            
            all_parcels.append({
                'barcode': barcode,
                'address': address,
                'recipient': recipient
            })
        
        # Create parcels in parallel batches (much faster)
        batch_size = 50
        for i in range(0, len(parcels_to_create), batch_size):
            batch = parcels_to_create[i:i + batch_size]
            tasks = [db.register_parcel(**parcel_data) for parcel_data in batch]
            await asyncio.gather(*tasks)
            print(f"   Created {min(i + batch_size, len(parcels_to_create))}/500 unique parcels...")
        
        print(f"   ✅ Created 500 parcels with unique addresses")
        
        print(f"\n📦 STEP 3: Creating 100 parcels with duplicate addresses...")
        
        # Select 100 random addresses from the first 500 to duplicate
        duplicate_indices = random.sample(range(500), 100)
        
        # Prepare duplicate parcels (in-memory)
        duplicate_parcels_to_create = []
        for dup_idx in duplicate_indices:
            barcode = f"DT{datetime.now().strftime('%Y%m%d')}{parcel_counter:04d}"
            parcel_counter += 1
            
            # Use same address but different recipient
            original_address = unique_addresses[dup_idx]
            
            # Create variation - different person at same address
            recipient = fake.name()
            phone = f"+61 4{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"
            priority = random.choice(['normal', 'normal', 'normal', 'urgent'])
            
            duplicate_parcels_to_create.append({
                'barcode': barcode,
                'sender_name': "DT Logistics Warehouse",
                'sender_address': "1 Homebush Bay Drive, Rhodes NSW 2138",
                'sender_phone': "+61 2 9999 0000",
                'recipient_name': recipient,
                'recipient_address': original_address,
                'recipient_phone': phone,
                'destination_postcode': original_address.split()[-1],
                'destination_state': "NSW",
                'service_type': priority,
                'special_instructions': random.choice([
                    "Leave with reception",
                    "Multiple packages expected",
                    "Signature required",
                    "Leave at front door",
                    "Ring doorbell twice"
                ])
            })
            
            all_parcels.append({
                'barcode': barcode,
                'address': original_address,
                'recipient': recipient
            })
        
        # Create duplicate parcels in batches
        batch_size = 50
        for i in range(0, len(duplicate_parcels_to_create), batch_size):
            batch = duplicate_parcels_to_create[i:i + batch_size]
            tasks = [db.register_parcel(**parcel_data) for parcel_data in batch]
            await asyncio.gather(*tasks)
        
        print(f"   ✅ Created 100 duplicate address parcels")
        print(f"   📊 Total parcels: {len(all_parcels)}")
        
        print(f"\n👥 STEP 4: Creating driver manifests...")
        
        # Shuffle all parcels before distribution
        random.shuffle(all_parcels)
        
        # Create manifests for first 3 drivers (for demo)
        drivers = [
            {'id': 'driver-001', 'name': 'John Smith', 'num_parcels': 35},
            {'id': 'driver-002', 'name': 'Maria Garcia', 'num_parcels': 40},
            {'id': 'driver-003', 'name': 'David Wong', 'num_parcels': 45}
        ]
        
        parcel_index = 0
        
        for driver in drivers:
            # Get this driver's parcels
            driver_parcels = all_parcels[parcel_index:parcel_index + driver['num_parcels']]
            driver_barcodes = [p['barcode'] for p in driver_parcels]
            
            manifest_id = await db.create_driver_manifest(
                driver_id=driver['id'],
                driver_name=driver['name'],
                parcel_barcodes=driver_barcodes,
                driver_state='NSW'
            )
            
            # Calculate unique vs duplicate addresses for this driver
            driver_addresses = [p['address'] for p in driver_parcels]
            unique_addrs = set(driver_addresses)
            duplicate_count = len(driver_addresses) - len(unique_addrs)
            
            print(f"\n   ✅ {driver['name']} ({driver['id']})")
            print(f"      Manifest: {manifest_id}")
            print(f"      Total parcels: {len(driver_barcodes)}")
            print(f"      Unique addresses: {len(unique_addrs)}")
            print(f"      Duplicate addresses: {duplicate_count}")
            
            parcel_index += driver['num_parcels']
        
        # Store remaining parcels for future drivers
        remaining_parcels = all_parcels[parcel_index:]
        print(f"\n   📦 Remaining parcels for other drivers: {len(remaining_parcels)}")
        
        print(f"\n{'='*80}")
        print("📊 ADDRESS DIVERSITY ANALYSIS")
        print("="*80)
        
        # Check address overlap between first 3 drivers
        for i, driver1 in enumerate(drivers):
            for driver2 in drivers[i+1:]:
                manifest1 = await db.get_driver_manifest(driver1['id'])
                manifest2 = await db.get_driver_manifest(driver2['id'])
                
                addrs1 = set(item['recipient_address'] for item in manifest1['items'])
                addrs2 = set(item['recipient_address'] for item in manifest2['items'])
                
                overlap = addrs1 & addrs2
                total_unique = len(addrs1 | addrs2)
                uniqueness_pct = ((total_unique - len(overlap)) / total_unique) * 100 if total_unique > 0 else 0
                
                print(f"\n{driver1['name']} vs {driver2['name']}:")
                print(f"   {driver1['name']}: {len(addrs1)} unique addresses")
                print(f"   {driver2['name']}: {len(addrs2)} unique addresses")
                print(f"   Shared addresses: {len(overlap)}")
                print(f"   Overall uniqueness: {uniqueness_pct:.1f}%")
                
                if uniqueness_pct >= 80:
                    print(f"   ✅ Target met (≥80% unique)")
                else:
                    print(f"   ⚠️  Below target (<80% unique)")
        
        print(f"\n{'='*80}")
        print("✅ REGENERATION COMPLETE!")
        print("="*80)
        print(f"\n📊 Summary:")
        print(f"   • Total parcels created: 600")
        print(f"   • Unique addresses: 500")
        print(f"   • Duplicate addresses: 100")
        print(f"   • Drivers with manifests: 3")
        print(f"   • Parcels available for other drivers: {len(remaining_parcels)}")
        print(f"\n💡 Next steps:")
        print(f"   1. Run: python reset_all_drivers.py")
        print(f"   2. Log in as driver-001, driver-002, or driver-003")
        print(f"   3. Watch route optimization group duplicate addresses!")

if __name__ == '__main__':
    asyncio.run(regenerate_driver_parcels())
