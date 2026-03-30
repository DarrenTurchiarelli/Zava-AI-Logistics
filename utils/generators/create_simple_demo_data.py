#!/usr/bin/env python3
"""
Simple script to create driver manifests and approval requests
Uses existing parcels, avoids complex queries
"""

import asyncio
import os
import sys
import random
from datetime import datetime, timedelta

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from parcel_tracking_db import ParcelTrackingDB

# List of all 57 drivers
DRIVERS = [f"driver-{str(i).zfill(3)}" for i in range(1, 58)]


async def create_simple_manifests():
    """Create manifests for all drivers using existing parcels"""
    
    print("\n" + "=" * 70)
    print("Simple Manifest & Approval Generator")
    print("=" * 70)
    
    async with ParcelTrackingDB() as db:
        # Get all existing parcels
        print("\n📦 Fetching existing parcels...")
        all_parcels = await db.get_all_parcels()
        print(f"✓ Found {len(all_parcels)} parcels")
        
        if len(all_parcels) < 100:
            print("❌ Not enough parcels. Need at least 100.")
            return
        
        # Update some parcels to "Out for Delivery" status
        print("\n🔄 Updating parcels to 'Out for Delivery' status...")
        container = db.database.get_container_client(db.parcels_container)
        
        parcels_for_delivery = []
        for i, parcel in enumerate(all_parcels[:500]):  # Use first 500 parcels
            try:
                # Use store_location as partition key (not barcode)
                partition_key = parcel.get('store_location', 'unknown')
                
                parcel_doc = await container.read_item(
                    item=parcel['id'],
                    partition_key=partition_key
                )
                
                # Update status
                parcel_doc['current_status'] = 'Out for Delivery'
                parcel_doc['current_location'] = 'Delivery Vehicle'
                
                await container.replace_item(
                    item=parcel_doc['id'],
                    body=parcel_doc
                )
                
                parcels_for_delivery.append(parcel_doc)
                
                if (i + 1) % 50 == 0:
                    print(f"  Updated {i + 1} parcels...")
                    
            except Exception as e:
                # Skip parcels with issues
                if (i + 1) % 100 == 0:
                    print(f"  Processed {i + 1} parcels ({len(parcels_for_delivery)} successful)...")
                continue
        
        print(f"✓ Updated {len(parcels_for_delivery)} parcels to 'Out for Delivery'")
        
        # Create manifests for drivers
        print(f"\n📋 Creating manifests for {len(DRIVERS)} drivers...")
        
        manifests_container = db.database.get_container_client(db.manifests_container)
        
        # Divide parcels among drivers (7-10 parcels each)
        random.shuffle(parcels_for_delivery)
        parcel_index = 0
        manifests_created = 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        for driver_id in DRIVERS:
            # Assign 7-10 parcels to this driver
            num_parcels = random.randint(7, 10)
            driver_parcels = parcels_for_delivery[parcel_index:parcel_index + num_parcels]
            parcel_index += num_parcels
            
            if not driver_parcels or parcel_index >= len(parcels_for_delivery):
                break
            
            # Create manifest document
            manifest_id = f"M{datetime.now().strftime('%Y%m%d')}{driver_id.split('-')[1]}"
            
            manifest = {
                'id': manifest_id,
                'manifest_id': manifest_id,
                'driver_user_id': driver_id,
                'driver_name': f"Driver {driver_id.split('-')[1]}",
                'delivery_date': today,
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'parcels': [
                    {
                        'tracking_number': p.get('tracking_number'),
                        'barcode': p.get('barcode') or p.get('id'),
                        'recipient_name': p.get('recipient_name', 'Unknown'),
                        'recipient_address': p.get('recipient_address', 'Unknown'),
                        'priority': random.choice(['normal', 'normal', 'urgent']),
                        'status': 'pending'
                    }
                    for p in driver_parcels
                ],
                'route_optimized': False,
                'total_stops': len(driver_parcels)
            }
            
            try:
                await manifests_container.create_item(body=manifest)
                manifests_created += 1
                
                if manifests_created % 10 == 0:
                    print(f"  Created {manifests_created} manifests...")
                    
            except Exception as e:
                print(f"  ⚠ Failed to create manifest for {driver_id}: {str(e)[:80]}")
        
        print(f"✓ Created {manifests_created} manifests")
        
        # Create approval requests
        print("\n⚖️ Creating approval demo requests...")
        
        # Get some random parcels for approval requests
        approval_parcels = random.sample(all_parcels[:200], min(11, len(all_parcels)))
        
        approval_types = [
            'address_change',
            'delivery_attempt_failed',
            'signature_exception',
            'special_handling',
            'address_change',
            'delivery_confirmation',
            'address_change',
            'signature_exception',
            'special_handling',
            'delivery_attempt_failed',
            'delivery_confirmation'
        ]
        
        approvals_created = 0
        
        for i, parcel in enumerate(approval_parcels):
            request_type = approval_types[i] if i < len(approval_types) else 'address_change'
            
            approval_doc = {
                'id': f"AR{datetime.now().strftime('%Y%m%d%H%M%S')}{str(i).zfill(3)}",
                'request_id': f"AR{datetime.now().strftime('%Y%m%d')}{str(i + 1).zfill(3)}",
                'tracking_number': parcel.get('tracking_number'),
                'barcode': parcel.get('barcode') or parcel.get('id'),
                'request_type': request_type,
                'status': 'pending',
                'requested_by': 'system',
                'requested_at': datetime.now().isoformat(),
                'parcel_dc': parcel.get('store_location', 'DC-SYD-001'),
                'parcel_status': parcel.get('current_status', 'registered'),
                'priority': 'normal' if i % 3 != 0 else 'high',
                'details': f"Request for {request_type} on parcel {parcel.get('tracking_number')}"
            }
            
            try:
                await db.request_approval(
                    parcel_barcode=approval_doc['barcode'],
                    request_type=approval_doc['request_type'],
                    requested_by=approval_doc['requested_by'],
                    details=approval_doc['details']
                )
                approvals_created += 1
            except Exception as e:
                print(f"  ⚠ Failed to create approval {i + 1}: {str(e)[:60]}")
        
        print(f"✓ Created {approvals_created} approval requests")
        
        print("\n" + "=" * 70)
        print("✅ Generation Complete!")
        print("=" * 70)
        print(f"\nCreated:")
        print(f"  • {manifests_created} driver manifests")
        print(f"  • {approvals_created} approval requests")
        print(f"  • {len(parcels_for_delivery)} parcels set to 'Out for Delivery'")
        print("\nNext steps:")
        print("1. Login as driver001 (password: driver123)")
        print("2. Go to /manifest to see assigned parcels")
        print("3. Login as depot_mgr (password: depot123)")
        print("4. Go to /approvals to see pending requests")


if __name__ == "__main__":
    asyncio.run(create_simple_manifests())
