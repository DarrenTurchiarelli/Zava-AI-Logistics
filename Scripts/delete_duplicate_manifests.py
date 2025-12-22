"""
Delete Duplicate Driver Manifests
==================================
This script removes duplicate manifests for the same driver on the same date,
keeping only the most recent one based on created_timestamp.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parcel_tracking_db import ParcelTrackingDB

async def delete_duplicate_manifests():
    """Find and delete duplicate manifests, keeping only the most recent per driver per date"""
    
    print("=" * 80)
    print("DELETE DUPLICATE DRIVER MANIFESTS")
    print("=" * 80)
    
    async with ParcelTrackingDB() as db:
        if not db.database:
            await db.connect()
        
        # Get the manifests container
        container = db.database.get_container_client("driver_manifests")
        
        # Get all active manifests (no ORDER BY due to missing composite index)
        query = "SELECT * FROM c WHERE c.status = 'active'"
        
        manifests = []
        async for manifest in container.query_items(query=query):
            manifests.append(manifest)
        
        # Sort in memory after fetching
        manifests.sort(key=lambda x: (x['driver_id'], x['manifest_date'], x.get('created_timestamp', '')), reverse=False)
        
        print(f"\n📋 Found {len(manifests)} active manifests")
        
        if not manifests:
            print("✅ No manifests to process")
            return
        
        # Group manifests by driver_id and manifest_date
        manifest_groups = {}
        for manifest in manifests:
            key = (manifest['driver_id'], manifest['manifest_date'])
            if key not in manifest_groups:
                manifest_groups[key] = []
            manifest_groups[key].append(manifest)
        
        # Find duplicates
        duplicates_to_delete = []
        drivers_processed = set()
        
        for (driver_id, manifest_date), group_manifests in manifest_groups.items():
            if len(group_manifests) > 1:
                # Sort by created_timestamp descending (most recent first)
                group_manifests.sort(key=lambda x: x.get('created_timestamp', ''), reverse=True)
                
                # Keep the first (most recent), mark the rest for deletion
                keep_manifest = group_manifests[0]
                delete_manifests = group_manifests[1:]
                
                print(f"\n👤 Driver: {driver_id} | Date: {manifest_date}")
                print(f"   ✅ KEEPING: {keep_manifest['id']} (created: {keep_manifest.get('created_timestamp', 'N/A')})")
                print(f"   ❌ DELETING {len(delete_manifests)} duplicate(s):")
                
                for dm in delete_manifests:
                    print(f"      - {dm['id']} (created: {dm.get('created_timestamp', 'N/A')})")
                    duplicates_to_delete.append(dm)
                
                drivers_processed.add(driver_id)
        
        # Summary
        print(f"\n" + "=" * 80)
        print(f"📊 SUMMARY:")
        print(f"   Total manifests: {len(manifests)}")
        print(f"   Drivers with duplicates: {len(drivers_processed)}")
        print(f"   Duplicates to delete: {len(duplicates_to_delete)}")
        print("=" * 80)
        
        if not duplicates_to_delete:
            print("\n✅ No duplicate manifests found!")
            return
        
        # Confirm deletion
        print(f"\n⚠️  This will DELETE {len(duplicates_to_delete)} duplicate manifest(s)")
        response = input("Continue? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("❌ Operation cancelled")
            return
        
        # Delete duplicates and reset their parcels
        deleted_count = 0
        parcels_reset = 0
        
        parcels_container = db.database.get_container_client("parcels")
        
        for manifest in duplicates_to_delete:
            try:
                manifest_id = manifest['id']
                
                # First, find all parcels assigned to this manifest
                parcel_query = """
                    SELECT * FROM c 
                    WHERE IS_DEFINED(c.assigned_manifest) 
                    AND c.assigned_manifest = @manifest_id
                """
                parcel_params = [{"name": "@manifest_id", "value": manifest_id}]
                
                parcels_in_manifest = []
                async for parcel in parcels_container.query_items(query=parcel_query, parameters=parcel_params):
                    parcels_in_manifest.append(parcel)
                
                # Reset each parcel back to depot
                for parcel in parcels_in_manifest:
                    try:
                        parcel['current_status'] = 'at_depot'
                        parcel['assigned_driver'] = None
                        parcel['assigned_manifest'] = None
                        
                        await parcels_container.replace_item(
                            item=parcel['id'],
                            body=parcel
                        )
                        parcels_reset += 1
                    except Exception as e:
                        print(f"   ⚠️  Error resetting parcel {parcel.get('barcode', parcel['id'])}: {e}")
                
                # Now delete the manifest
                await container.delete_item(
                    item=manifest_id,
                    partition_key=manifest_id
                )
                deleted_count += 1
                print(f"✅ Deleted manifest {manifest_id} and reset {len(parcels_in_manifest)} parcel(s) to depot")
                
            except Exception as e:
                print(f"❌ Error deleting manifest {manifest['id']}: {e}")
        
        print(f"\n" + "=" * 80)
        print(f"✅ COMPLETED:")
        print(f"   Deleted manifests: {deleted_count}")
        print(f"   Parcels reset to depot: {parcels_reset}")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(delete_duplicate_manifests())
