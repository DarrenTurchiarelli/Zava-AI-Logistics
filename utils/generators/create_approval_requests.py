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
            # delivery_attempts is where the app reads pending approvals from
            # (get_all_pending_approvals queries delivery_attempts WHERE status='pending'
            #  AND IS_DEFINED(request_type))
            approval_container = db.database.get_container_client("delivery_attempts")
            
            # Clear any existing pending approval requests (contraband scenarios)
            print("\n🗑️  Clearing existing pending approval requests from delivery_attempts...")
            existing_approvals = [
                a async for a in approval_container.query_items(
                    "SELECT c.id, c.barcode FROM c WHERE c.status = 'pending' AND IS_DEFINED(c.request_type)"
                )
            ]
            for ea in existing_approvals:
                try:
                    await approval_container.delete_item(ea["id"], partition_key=ea.get("barcode", ea["id"]))
                except Exception:
                    pass
            print(f"   Cleared {len(existing_approvals)} old approval requests.")

            # Get existing parcels with pending/at-depot status for contraband scenarios
            print("\n📦 Finding existing parcels at distribution centres...")
            query = "SELECT TOP 15 * FROM c WHERE c.current_status IN ('At Depot', 'Sorting', 'pending') ORDER BY c.registration_timestamp DESC"
            parcels = [p async for p in parcels_container.query_items(query)]

            # Contraband / suspicious-destination scenarios
            # All parcels remain at the DC (pending) — they cannot be dispatched until approved
            SCENARIOS = [
                {
                    "type": "contraband_detection",
                    "desc": "X-ray scan detected dense metallic objects consistent with firearms",
                    "contraband_type": "Suspected Firearms",
                    "reason": "Automated X-ray flagged high-density metallic mass. Package weight inconsistent with declared contents (\"gift items\"). Requires physical inspection before any release.",
                    "priority": "critical",
                    "agencies": ["Australian Federal Police", "Border Force"],
                    "cat": "🔴 CRITICAL",
                },
                {
                    "type": "contraband_detection",
                    "desc": "Narcotics canine alert — chemical trace confirmed by field test",
                    "contraband_type": "Suspected Narcotics",
                    "reason": "Drug detection dog alerted on package. Field swab returned positive for methamphetamine residue. Sender address flagged in law enforcement database.",
                    "priority": "critical",
                    "agencies": ["Australian Federal Police", "Border Force", "State Police"],
                    "cat": "🔴 CRITICAL",
                },
                {
                    "type": "contraband_detection",
                    "desc": "Package contents match profile for unregistered pyrotechnics/explosives",
                    "contraband_type": "Suspected Fireworks / Explosives",
                    "reason": "Declared as \"party supplies\" but packing density, weight, and thermal signature consistent with commercial fireworks. Recipient has no pyrotechnics licence on file.",
                    "priority": "critical",
                    "agencies": ["Australian Federal Police", "Fire & Rescue NSW"],
                    "cat": "🔴 CRITICAL",
                },
                {
                    "type": "contraband_detection",
                    "desc": "Unmarked pharmaceutical packaging — controlled substances import suspected",
                    "contraband_type": "Suspected Controlled Pharmaceuticals",
                    "reason": "Package contains blister packs with no TGA registration markings. Sender is a known overseas grey-market supplier. Import quantity exceeds personal-use threshold.",
                    "priority": "high",
                    "agencies": ["Therapeutic Goods Administration", "Border Force"],
                    "cat": "🔴 HIGH",
                },
                {
                    "type": "contraband_detection",
                    "desc": "Ammunition detected — unlicensed import of live rounds",
                    "contraband_type": "Suspected Ammunition",
                    "reason": "XRF scan shows lead and brass components matching small-arms cartridge profile. Recipient holds no firearms licence. Declared as \"metal brackets\".",
                    "priority": "critical",
                    "agencies": ["Australian Federal Police", "Border Force", "State Police"],
                    "cat": "🔴 CRITICAL",
                },
                {
                    "type": "suspicious_destination",
                    "desc": "Destination flagged — AUSTRAC suspicious activity report active",
                    "contraband_type": "Suspicious Destination",
                    "reason": "Recipient address is subject to an active AUSTRAC financial intelligence alert linked to money-laundering investigation. High-value goods ($3,200 declared).",
                    "priority": "high",
                    "agencies": ["AUSTRAC", "Australian Federal Police"],
                    "cat": "🟠 HIGH",
                },
                {
                    "type": "suspicious_destination",
                    "desc": "Recipient on DFAT sanctioned entities list",
                    "contraband_type": "Sanctions Violation",
                    "reason": "Name and address match a record on the Australian Department of Foreign Affairs and Trade sanctions register. Export prohibited under the Autonomous Sanctions Act 2011.",
                    "priority": "critical",
                    "agencies": ["DFAT Sanctions Unit", "Border Force"],
                    "cat": "🔴 CRITICAL",
                },
                {
                    "type": "suspicious_destination",
                    "desc": "Unusual routing — parcel diverted three times through known reshipping hubs",
                    "contraband_type": "Suspicious Routing",
                    "reason": "Origin: Shenzhen → Singapore → Dubai → Sydney. Reshipping pattern matches known contraband trafficking route. Declared value ($45) inconsistent with actual weight (6.2 kg).",
                    "priority": "high",
                    "agencies": ["Border Force", "Australian Federal Police"],
                    "cat": "🟠 HIGH",
                },
                {
                    "type": "customs_hold",
                    "desc": "CITES protected species — wildlife smuggling suspected",
                    "contraband_type": "Wildlife / CITES Violation",
                    "reason": "Customs inspection revealed dried biological material matching CITES Appendix I protected species. Import without CITES permit is a criminal offence under EPBC Act.",
                    "priority": "critical",
                    "agencies": ["Border Force", "Dept of Agriculture (Biosecurity)", "Australian Federal Police"],
                    "cat": "🔴 CRITICAL",
                },
                {
                    "type": "customs_hold",
                    "desc": "Biosecurity risk — undeclared organic material detected",
                    "contraband_type": "Biosecurity / Undeclared Organic Material",
                    "reason": "Beagle brigade detection. Package contains undeclared seeds and dried plant matter. High risk of exotic pest introduction. Quarantine hold applied under Biosecurity Act 2015.",
                    "priority": "high",
                    "agencies": ["Dept of Agriculture (Biosecurity)", "Border Force"],
                    "cat": "🟠 HIGH",
                },
                {
                    "type": "contraband_detection",
                    "desc": "Counterfeit goods — trademark infringement, large volume",
                    "contraband_type": "Counterfeit Goods",
                    "reason": "Contents appear to be counterfeit luxury electronics. Serial numbers do not match authentic product database. Commercial quantity (240 units) indicates commercial fraud intent.",
                    "priority": "medium",
                    "agencies": ["Australian Border Force", "IP Australia"],
                    "cat": "🟡 MEDIUM",
                },
            ]

            if len(parcels) < len(SCENARIOS):
                print(f"⚠️  Only found {len(parcels)} parcels (need {len(SCENARIOS)})")
                print("   Creating placeholder parcels at distribution centres...")
                DC_LIST = ["DC-SYD-001", "DC-MEL-001", "DC-BNE-001", "DC-PER-001", "DC-ADL-001"]
                for i in range(len(SCENARIOS) - len(parcels)):
                    p = {
                        "id": str(uuid.uuid4()),
                        "barcode": f"HOLD{datetime.now().strftime('%Y%m%d')}{i:03d}",
                        "tracking_number": f"HD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}",
                        "sender_name": "International Sender",
                        "sender_address": "Unknown Overseas Origin",
                        "sender_phone": "+61400000000",
                        "recipient_name": f"Flagged Recipient {i + 1}",
                        "recipient_address": f"{100 + i} Flagged Street, Sydney NSW 2000",
                        "recipient_phone": "+61400000001",
                        "destination_postcode": "2000",
                        "destination_state": "NSW",
                        "destination_city": "Sydney",
                        "service_type": "standard",
                        "weight": round(1.5 + i * 0.7, 1),
                        "dimensions": "30x20x15",
                        "declared_value": [45, 120, 280, 3200, 1800, 950, 75, 600, 2100, 380, 160][i % 11],
                        "store_location": DC_LIST[i % len(DC_LIST)],
                        "origin_location": DC_LIST[i % len(DC_LIST)],
                        "current_location": DC_LIST[i % len(DC_LIST)],
                        "current_status": "pending",
                        "fraud_risk_score": [88, 92, 85, 76, 95, 82, 70, 88, 97, 79, 65][i % 11],
                        "registration_timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    await parcels_container.upsert_item(p)
                    parcels.append(p)
                    print(f"   ✓ Created placeholder {p['barcode']}")

            # Force all approval parcels to pending status at their DC
            for parcel in parcels[: len(SCENARIOS)]:
                dc = parcel.get("store_location") or parcel.get("origin_location") or "DC-SYD-001"
                update_needed = (
                    parcel.get("current_status") not in ("pending", "At Depot", "Sorting")
                    or parcel.get("current_location") != dc
                )
                if update_needed:
                    parcel["current_status"] = "pending"
                    parcel["current_location"] = dc
                    await parcels_container.upsert_item(parcel)

            print(f"✓ Using {min(len(parcels), len(SCENARIOS))} parcels\n")

            created = 0
            for i, scenario in enumerate(SCENARIOS[: len(parcels)]):
                parcel = parcels[i]

                dc = parcel.get("store_location") or parcel.get("origin_location") or "DC-SYD-001"
                barcode = parcel["barcode"]
                request = {
                    "id": str(uuid.uuid4()),
                    # partition key for delivery_attempts container is /barcode
                    "barcode": barcode,
                    "parcel_barcode": barcode,
                    "request_type": scenario["type"],
                    "description": scenario["desc"],
                    "contraband_type": scenario["contraband_type"],
                    "reason": scenario["reason"],
                    "escalate_agencies": scenario["agencies"],
                    "priority": scenario["priority"],
                    "requested_by": "Automated Screening System",
                    "status": "pending",
                    "approved_by": None,
                    "approval_timestamp": None,
                    "comments": None,
                    "parcel_dc": dc,
                    "parcel_status": "pending",
                    "parcel_location": dc,
                    "request_timestamp": datetime.now(timezone.utc).isoformat(),
                }

                await approval_container.create_item(body=request)
                created += 1
                print(f"   {scenario['cat']:12} {parcel['barcode'][:20]:20} — {scenario['contraband_type']}")
            
            print("\n" + "=" * 70)
            print(f"✅ Created {created} contraband/suspicious approval requests")
            print("   All parcels held at Distribution Centre (status: pending)")
            print("=" * 70)
            print("\n📋 Demo Ready!")
            print("   Login: https://<webapp>.azurewebsites.net/login")
            print("   User: depot_mgr / depot123")
            print("   Page: Approvals — each tile has an Escalate button\n")
            
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(create_approval_requests())
    sys.exit(0 if success else 1)
