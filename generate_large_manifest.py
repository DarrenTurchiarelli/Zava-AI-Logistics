"""Generate a driver manifest with 100+ parcels for scalability testing"""
import asyncio
import random
from datetime import datetime
from faker import Faker
from parcel_tracking_db import ParcelTrackingDB

# Initialize Faker for Australian addresses
fake = Faker('en_AU')

async def generate_large_manifest(num_parcels=120):
    """Generate a single driver manifest with 100+ parcels"""
    
    async with ParcelTrackingDB() as db:
        print("\n" + "="*80)
        print(f"🔄 GENERATING {num_parcels} PARCELS FOR DRIVER-004 (SCALABILITY TEST)")
        print("="*80)
        
        # Delete existing manifest for driver-004
        manifest_container = db.database.get_container_client('driver_manifests')
        query = 'SELECT * FROM c WHERE c.driver_id = "driver-004"'
        
        async for manifest in manifest_container.query_items(query=query):
            await manifest_container.delete_item(item=manifest['id'], partition_key=manifest['driver_id'])
            print(f"   Deleted existing manifest: {manifest['id']}")
        
        # Delete old parcels for this test
        parcels_container = db.database.get_container_client('parcels')
        query = "SELECT * FROM c WHERE STARTSWITH(c.barcode, 'DT20251215TEST')"
        
        deleted_count = 0
        async for parcel in parcels_container.query_items(query=query):
            try:
                await parcels_container.delete_item(item=parcel['id'], partition_key=parcel['barcode'])
                deleted_count += 1
            except Exception:
                pass
        
        print(f"   Deleted {deleted_count} old test parcels")
        
        print(f"\n📍 Generating {num_parcels} Sydney addresses...")
        
        # Generate addresses
        addresses = []
        recipients = []
        used_addresses = set()
        
        sydney_postcodes = ['2000', '2007', '2008', '2009', '2010', '2021', '2026', '2028', 
                           '2037', '2040', '2042', '2048', '2060', '2061', '2065', '2088',
                           '2090', '2095', '2096', '2100', '2101', '2110', '2111', '2113']
        
        while len(addresses) < num_parcels:
            street_address = fake.street_address()
            suburb = fake.city()
            postcode = random.choice(sydney_postcodes)
            address = f"{street_address}, {suburb} NSW {postcode}"
            
            if address not in used_addresses:
                used_addresses.add(address)
                addresses.append(address)
                recipients.append(fake.name())
        
        print(f"   ✅ Generated {len(addresses)} unique addresses")
        
        print(f"\n📦 Creating {num_parcels} parcels...")
        
        parcel_counter = 1
        all_parcels = []
        parcels_to_create = []
        
        for i in range(num_parcels):
            barcode = f"DT20251215TEST{parcel_counter:04d}"
            parcel_counter += 1
            
            address = addresses[i]
            recipient = recipients[i]
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
        
        # Create parcels in parallel batches
        batch_size = 50
        for i in range(0, len(parcels_to_create), batch_size):
            batch = parcels_to_create[i:i + batch_size]
            tasks = [db.register_parcel(**parcel_data) for parcel_data in batch]
            await asyncio.gather(*tasks)
            print(f"   Created {min(i + batch_size, len(parcels_to_create))}/{num_parcels} parcels...")
        
        print(f"   ✅ Created {num_parcels} parcels")
        
        print(f"\n🚚 Creating driver manifest for Driver 004...")
        
        # Create manifest
        manifest_id = await db.create_driver_manifest(
            driver_id="driver-004",
            driver_name="Test Driver (Scalability)",
            parcel_barcodes=[p['barcode'] for p in all_parcels]
        )
        
        print(f"   ✅ Created manifest: {manifest_id}")
        print(f"\n{'='*80}")
        print(f"✅ COMPLETE! Test with driver-004 / Password123!")
        print(f"   Manifest: {manifest_id}")
        print(f"   Parcels: {num_parcels}")
        print(f"{'='*80}\n")

if __name__ == '__main__':
    import sys
    num_parcels = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    asyncio.run(generate_large_manifest(num_parcels))
