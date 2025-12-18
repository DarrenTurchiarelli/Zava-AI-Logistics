#!/usr/bin/env python3
"""
Cleanup Duplicate Parcels Script

This script identifies and removes duplicate parcels based on barcode.
When duplicates exist, it keeps the OLDEST parcel (first created) and removes newer duplicates.

Usage:
    # Dry run (preview duplicates without deleting)
    python Scripts/cleanup_duplicate_parcels.py
    
    # Actually delete duplicates
    python Scripts/cleanup_duplicate_parcels.py --delete
"""

import asyncio
import sys
import os
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

# Add parent directory to path to import ParcelTrackingDB
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parcel_tracking_db import ParcelTrackingDB


async def find_duplicate_parcels(db: ParcelTrackingDB) -> Dict[str, List[Dict[str, Any]]]:
    """
    Find all parcels that have duplicate barcodes
    
    Returns:
        Dictionary mapping barcode to list of duplicate parcels
    """
    print("🔍 Scanning database for duplicate parcels...")
    
    # Get all parcels
    parcels = await db.get_all_parcels()
    
    # Group parcels by barcode
    barcode_groups = defaultdict(list)
    for parcel in parcels:
        barcode = parcel.get('barcode')
        if barcode:
            barcode_groups[barcode].append(parcel)
    
    # Find duplicates (barcodes with more than one parcel)
    duplicates = {
        barcode: parcels_list 
        for barcode, parcels_list in barcode_groups.items() 
        if len(parcels_list) > 1
    }
    
    return duplicates


async def display_duplicates(duplicates: Dict[str, List[Dict[str, Any]]]) -> None:
    """Display information about duplicate parcels"""
    
    if not duplicates:
        print("\n✅ No duplicate parcels found! Database is clean.")
        return
    
    total_duplicates = sum(len(parcels) - 1 for parcels in duplicates.values())
    
    print(f"\n⚠️  Found {len(duplicates)} barcodes with duplicates ({total_duplicates} duplicate records)")
    print("=" * 80)
    
    for barcode, parcels_list in sorted(duplicates.items()):
        print(f"\n📦 Barcode: {barcode} ({len(parcels_list)} copies)")
        
        # Sort by created_at to identify oldest
        parcels_sorted = sorted(
            parcels_list, 
            key=lambda p: p.get('created_at', '9999-12-31T23:59:59Z')
        )
        
        for idx, parcel in enumerate(parcels_sorted):
            marker = "✅ KEEP" if idx == 0 else "❌ DELETE"
            created = parcel.get('created_at', 'Unknown')
            tracking = parcel.get('tracking_number', 'N/A')
            recipient = parcel.get('recipient_name', 'Unknown')
            status = parcel.get('current_status', 'unknown')
            parcel_id = parcel.get('id')
            
            print(f"  {marker} [{idx+1}] Created: {created}")
            print(f"      ID: {parcel_id}")
            print(f"      Tracking: {tracking}")
            print(f"      Recipient: {recipient}")
            print(f"      Status: {status}")


async def delete_duplicate_parcels(db: ParcelTrackingDB, duplicates: Dict[str, List[Dict[str, Any]]]) -> int:
    """
    Delete duplicate parcels, keeping only the oldest one for each barcode
    
    Returns:
        Number of parcels deleted
    """
    if not duplicates:
        return 0
    
    deleted_count = 0
    container = db.database.get_container_client(db.parcels_container)
    
    for barcode, parcels_list in duplicates.items():
        # Sort by created_at to identify oldest
        parcels_sorted = sorted(
            parcels_list, 
            key=lambda p: p.get('created_at', '9999-12-31T23:59:59Z')
        )
        
        # Keep the first (oldest), delete the rest
        for idx, parcel in enumerate(parcels_sorted[1:], start=1):
            try:
                parcel_id = parcel.get('id')
                partition_key = parcel.get('store_location', 'unknown')
                
                # Delete the duplicate parcel
                await container.delete_item(
                    item=parcel_id,
                    partition_key=partition_key
                )
                
                deleted_count += 1
                print(f"  ✅ Deleted duplicate {idx} for barcode {barcode} (ID: {parcel_id})")
                
            except Exception as e:
                print(f"  ❌ Error deleting parcel {parcel_id}: {e}")
    
    return deleted_count


async def cleanup_related_data(db: ParcelTrackingDB, deleted_parcels: List[str]) -> None:
    """
    Optional: Clean up tracking events and delivery attempts for deleted parcels
    
    Note: This is optional - you may want to keep historical data
    """
    # Placeholder for future implementation if needed
    pass


async def main():
    """Main cleanup process"""
    print("=" * 80)
    print("  Duplicate Parcel Cleanup Utility")
    print("=" * 80)
    print()
    
    # Check if --delete flag is provided
    delete_mode = '--delete' in sys.argv or '-d' in sys.argv
    
    if delete_mode:
        print("⚠️  DELETE MODE ENABLED - Duplicates will be removed")
        print("   Keeping oldest parcel for each barcode")
    else:
        print("🔍 DRY RUN MODE - No deletions will occur")
        print("   Use --delete flag to actually remove duplicates")
    print()
    
    try:
        async with ParcelTrackingDB() as db:
            # Find duplicates
            duplicates = await find_duplicate_parcels(db)
            
            # Display duplicates
            await display_duplicates(duplicates)
            
            if not duplicates:
                return
            
            # Delete if in delete mode
            if delete_mode:
                print("\n" + "=" * 80)
                
                # Confirm before deleting
                response = input("\n⚠️  Proceed with deletion? (yes/no): ").strip().lower()
                if response != 'yes':
                    print("❌ Deletion cancelled by user")
                    return
                
                print("\n🗑️  Deleting duplicate parcels...")
                deleted_count = await delete_duplicate_parcels(db, duplicates)
                
                print("\n" + "=" * 80)
                print(f"✅ Cleanup complete! Deleted {deleted_count} duplicate parcels")
                print("=" * 80)
            else:
                print("\n💡 To delete these duplicates, run:")
                print("   python Scripts/cleanup_duplicate_parcels.py --delete")
    
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
