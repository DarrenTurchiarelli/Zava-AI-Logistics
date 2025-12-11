"""
Generate fresh test data with parcels that have valid DC assignments
"""

import asyncio
from parcel_tracking_db import ParcelTrackingDB
from faker import Faker

fake = Faker('en_AU')

async def main():
    async with ParcelTrackingDB() as db:
        print("=" * 60)
        print("Creating parcels with valid DC assignments...")
        print("=" * 60)
        
        # Create parcels with statuses that will get real DCs:
        # - At Depot, Sorting, or In Transit (these get real DC codes)
        # We'll create 50 parcels with these statuses
        
        parcels_created = await db.add_random_test_parcels(50)
        print(f"✅ Created {len(parcels_created)} parcels")
        
        # Get all parcels and count how many have valid DCs
        all_parcels = await db.get_all_parcels()
        valid_dc_parcels = [
            p for p in all_parcels
            if p.get('origin_location') and 
            p.get('origin_location') not in ['Unknown DC', 'To Be Advised', 'Completed']
        ]
        
        print(f"\n📊 Database Statistics:")
        print(f"   Total parcels: {len(all_parcels)}")
        print(f"   Parcels with valid DCs: {len(valid_dc_parcels)}")
        print(f"   Parcels with invalid DCs: {len(all_parcels) - len(valid_dc_parcels)}")
        
        # Show sample of DC distribution
        dc_counts = {}
        for parcel in all_parcels:
            dc = parcel.get('origin_location', 'Unknown')
            dc_counts[dc] = dc_counts.get(dc, 0) + 1
        
        print(f"\n📍 DC Distribution (top 10):")
        sorted_dcs = sorted(dc_counts.items(), key=lambda x: x[1], reverse=True)
        for dc, count in sorted_dcs[:10]:
            print(f"   {dc}: {count} parcels")
        
        print("\n" + "=" * 60)
        print("Creating approval requests from valid-DC parcels...")
        print("=" * 60)
        
        # Now create approval requests (should only use parcels with valid DCs)
        approval_requests = await db.add_random_approval_requests(30)
        print(f"✅ Created {len(approval_requests)} approval requests")
        
        # Verify the new approvals have valid DCs
        all_approvals = await db.get_all_pending_approvals()
        print(f"\n📋 Total pending approvals: {len(all_approvals)}")
        
        valid_approvals = [
            a for a in all_approvals
            if a.get('parcel_dc') and 
            a.get('parcel_dc') not in ['Unknown DC', 'To Be Advised', 'Completed']
        ]
        
        print(f"   Approvals with valid DCs: {len(valid_approvals)}")
        print(f"   Approvals with invalid DCs: {len(all_approvals) - len(valid_approvals)}")
        
        if valid_approvals:
            print(f"\n✅ Sample of new approvals with valid DCs:")
            for i, approval in enumerate(valid_approvals[:5], 1):
                print(f"   {i}. {approval['parcel_barcode']} - {approval['request_type']}")
                print(f"      DC: {approval.get('parcel_dc')} | Status: {approval.get('parcel_status')}")
        
        print("\n" + "=" * 60)
        print("✅ Fresh test data generation complete!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
