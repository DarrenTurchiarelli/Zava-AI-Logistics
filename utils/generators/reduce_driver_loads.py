"""
Reduce Driver Loads - Remove half the parcels from each driver
================================================================

This script removes approximately 50% of parcels from each driver's manifest
to free up capacity for demonstrating the Dispatcher Agent.

Usage:
    python Scripts/reduce_driver_loads.py

This will:
- Find all drivers with assigned parcels
- Remove ~50% of parcels from each driver
- Reset those parcels to "at_depot" status (available for reassignment)
- Update manifest parcel counts
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parcel_tracking_db import ParcelTrackingDB


async def reduce_driver_loads():
    """Reduce driver parcel loads by 50%"""
    
    print("="*70)
    print("🚚 Reducing Driver Parcel Loads")
    print("="*70)
    
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        parcels_container = db.database.get_container_client(db.parcels_container)
        
        # Get all drivers with assigned parcels
        query = """
            SELECT DISTINCT c.assigned_driver 
            FROM c 
            WHERE IS_DEFINED(c.assigned_driver) AND c.assigned_driver != null
        """
        
        drivers = []
        async for item in parcels_container.query_items(query=query):
            drivers.append(item['assigned_driver'])
        
        print(f"\n📋 Found {len(drivers)} drivers with assigned parcels")
        
        total_unassigned = 0
        
        for driver_id in drivers:
            # Get all parcels for this driver
            query = """
                SELECT * FROM c 
                WHERE c.assigned_driver = @driver_id
            """
            parameters = [{"name": "@driver_id", "value": driver_id}]
            
            driver_parcels = []
            async for parcel in parcels_container.query_items(query=query, parameters=parameters):
                driver_parcels.append(parcel)
            
            if not driver_parcels:
                continue
            
            # Calculate how many to remove (half)
            total_parcels = len(driver_parcels)
            parcels_to_remove = total_parcels // 2
            
            if parcels_to_remove == 0:
                continue
            
            print(f"\n🚗 {driver_id}: {total_parcels} parcels → Removing {parcels_to_remove}")
            
            # Remove the first half
            for i, parcel in enumerate(driver_parcels[:parcels_to_remove]):
                # Reset parcel to unassigned state
                parcel['assigned_driver'] = None
                parcel['driver_name'] = None
                parcel['manifest_id'] = None
                parcel['assigned_timestamp'] = None
                parcel['current_status'] = 'at_depot'
                parcel['current_location'] = 'Central Distribution Centre'
                parcel['last_updated'] = datetime.now(timezone.utc).isoformat()
                
                # Update in database
                await parcels_container.upsert_item(parcel)
                total_unassigned += 1
                
                if (i + 1) % 10 == 0:
                    print(f"   ✓ Unassigned {i + 1}/{parcels_to_remove} parcels")
            
            print(f"   ✅ Completed: {driver_id} now has {total_parcels - parcels_to_remove} parcels")
        
        print(f"\n{'='*70}")
        print(f"✅ Successfully unassigned {total_unassigned} parcels")
        print(f"{'='*70}")
        print(f"\n📊 Summary:")
        print(f"   - Processed {len(drivers)} drivers")
        print(f"   - Freed up {total_unassigned} parcels")
        print(f"   - Parcels are now available for reassignment (status: at_depot)")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Navigate to: Drivers > Manage Manifests")
        print(f"   2. Click 'AI Auto-Assign Parcels'")
        print(f"   3. Watch Dispatcher Agent assign parcels to drivers with capacity")
        print("="*70)


if __name__ == "__main__":
    asyncio.run(reduce_driver_loads())
