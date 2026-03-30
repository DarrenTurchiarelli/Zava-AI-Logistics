"""
Create Approval Demo Requests
==============================
Run AFTER fresh deployment to add 11 approval requests for existing parcels.
Uses connection string from environment (set by deployment script).

Usage:
  From project root: python utils/generators/create_approval_requests.py
  From this folder:  python create_approval_requests.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

from parcel_tracking_db import ParcelTrackingDB


async def create_approval_requests():
    """Create 11 approval requests for existing parcels"""
    
    print("\n" + "=" * 70)
    print("Creating Approval Demo Requests")
    print("=" * 70)
    
    if not os.getenv('COSMOS_CONNECTION_STRING') and not os.getenv('COSMOS_DB_ENDPOINT'):
        print("\n❌ ERROR: No Cosmos DB credentials found!")
        print("   Run this from deploy_to_azure.ps1 or set COSMOS_CONNECTION_STRING")
        return False
    
    try:
        async with ParcelTrackingDB() as db:
            parcels_container = db.database.get_container_client("parcels")
            approval_container = db.database.get_container_client("approval_requests")
            
            # Get 15 existing parcels
            print("\n📦 Finding existing parcels...")
            query = "SELECT TOP 15 * FROM c WHERE c.current_status IN ('At Depot', 'In Transit') ORDER BY c.registration_timestamp DESC"
            parcels = [p async for p in parcels_container.query_items(query, enable_cross_partition_query=True)]
            
            if len(parcels) < 11:
                print(f"⚠️  Only found {len(parcels)} parcels (need 11)")
                print("   Creating minimal demo parcels...")
                
                # Create test parcels if needed
                for i in range(11 - len(parcels)):
                    p = {
                        "id": str(uuid.uuid4()),
                        "barcode": f"DEMO{datetime.now().strftime('%Y%m%d')}{i:03d}",
                        "tracking_number": f"LP{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}",
                        "sender_name": f"Demo Sender {i+1}",
                        "sender_address": "123 Test St, Sydney NSW 2000",
                        "sender_phone": "+61400000000",
                        "recipient_name": f"Demo Recipient {i+1}",
                        "recipient_address": "456 Demo Ave, Melbourne VIC 3000",
                        "recipient_phone": "+61400000001",
                        "destination_postcode": "3000",
                        "destination_state": "VIC",
                        "destination_city": "Melbourne",
                        "service_type": "standard",
                        "weight": 1.0,
                        "dimensions": "20x20x20",
                        "declared_value": [25, 75, 95, 1500, 200, 150, 3000, 2500, 1200, 800, 1800][i],
                        "store_location": "DC-SYD-001",
                        "origin_location": "DC-SYD-001",
                        "current_status": "At Depot",
                        "fraud_risk_score": [5, 8, 3, 85, 45, 35, 25, 45, 12, 38, 22][i],
                        "registration_timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    await parcels_container.upsert_item(p)
                    parcels.append(p)
                    print(f"   ✓ Created {p['barcode']}")
            
            print(f"✓ Using {len(parcels)} parcels\n")
            
            # 11 approval scenarios
            scenarios = [
                # AUTO-APPROVE (3)
                {"type": "delivery_confirmation", "desc": "Standard delivery - Verified sender", "priority": "low", "cat": "✅ AUTO-APPROVE"},
                {"type": "delivery_confirmation", "desc": "Delivery confirmation - Already delivered", "priority": "low", "cat": "✅ AUTO-APPROVE"},
                {"type": "delivery_redirect", "desc": "Address update - Verified recipient", "priority": "medium", "cat": "✅ AUTO-APPROVE"},
                # AUTO-DENY (4)
                {"type": "exception_handling", "desc": "Multiple address changes - HIGH FRAUD RISK", "priority": "high", "cat": "❌ AUTO-DENY"},
                {"type": "delivery_redirect", "desc": "BLACKLISTED address - fraud history", "priority": "critical", "cat": "❌ AUTO-DENY"},
                {"type": "delivery_redirect", "desc": "DUPLICATE request - processed twice today", "priority": "high", "cat": "❌ AUTO-DENY"},
                {"type": "damage_claim", "desc": "MISSING required documentation", "priority": "medium", "cat": "❌ AUTO-DENY"},
                # MANUAL REVIEW (4)
                {"type": "exception_handling", "desc": "High value ($2500) - alternative location", "priority": "high", "cat": "⚠️ MANUAL"},
                {"type": "delivery_redirect", "desc": "Time-sensitive medical - location change", "priority": "critical", "cat": "⚠️ MANUAL"},
                {"type": "return_to_sender", "desc": "Dispute - recipient claims never ordered", "priority": "medium", "cat": "⚠️ MANUAL"},
                {"type": "exception_handling", "desc": "Customs flagged - permit verification", "priority": "high", "cat": "⚠️ MANUAL"},
            ]
            
            created = 0
            for i, scenario in enumerate(scenarios[:len(parcels)]):
                parcel = parcels[i]
                
                # Check if request already exists
                existing_query = f"SELECT * FROM c WHERE c.parcel_barcode = '{parcel['barcode']}'"
                existing = [r async for r in approval_container.query_items(existing_query, enable_cross_partition_query=True)]
                
                if existing:
                    print(f"   ⏭️  {parcel['barcode'][:20]:20} - already has request")
                    continue
                
                request = {
                    "id": str(uuid.uuid4()),
                    "parcel_barcode": parcel["barcode"],
                    "request_type": scenario["type"],
                    "description": scenario["desc"],
                    "priority": scenario["priority"],
                    "requested_by": ["System", "Customer Service", "Security", "Depot Manager", "Customs"][i % 5],
                    "status": "pending",
                    "parcel_dc": parcel.get("store_location", "DC-SYD-001"),
                    "parcel_status": parcel.get("current_status", "At Depot"),
                    "request_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await approval_container.upsert_item(request)
                created += 1
                print(f"   {scenario['cat']:15} {parcel['barcode'][:20]}")
            
            print("\n" + "=" * 70)
            print(f"✅ Created {created} approval requests")
            print("=" * 70)
            print("\n📋 Demo Ready!")
            print("   Login: https://<webapp>.azurewebsites.net/login")
            print("   User: depot_mgr / depot123")
            print("   Page: Approvals\n")
            
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(create_approval_requests())
    sys.exit(0 if success else 1)
