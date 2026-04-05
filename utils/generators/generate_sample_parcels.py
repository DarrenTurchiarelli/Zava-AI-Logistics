"""
Generate Sample Parcels - Standalone Script
============================================
This script provides a simple interface for generating test data
for the Zava parcel tracking system.

Usage:
    python generate_sample_parcels.py
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone

from parcel_tracking_db import ParcelTrackingDB, initialize_company_information


async def generate_approval_demo_parcels(db: ParcelTrackingDB) -> dict:
    """
    Generate specialized parcels for demonstrating the approval agent mode.
    
    Creates parcels with specific characteristics that trigger:
    - Auto-approve scenarios (low risk, verified, standard)
    - Auto-deny scenarios (dangerous goods, high fraud risk, blacklisted)
    - Manual review scenarios (medium risk, high value, requires human judgment)
    
    Returns:
        dict: Summary of created parcels and approval requests by category
    """
    print("\n🤖 Generating Approval Demo Parcels...")
    print("=" * 60)
    
    # Get available DCs from the system
    distribution_centers = [
        "DC-SYD-001", "DC-SYD-002", "DC-MEL-001", "DC-MEL-002",
        "DC-BNE-001", "DC-PER-001", "DC-ADL-001", "DC-CAN-001"
    ]
    
    created_parcels = {
        "auto_approve": [],
        "auto_deny": [],
        "manual_review": []
    }
    
    # ==================== AUTO-APPROVE SCENARIOS ====================
    print("\n✅ Creating AUTO-APPROVE parcels...")
    
    # 1. Low risk, low value parcel
    parcel1 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}AA",
        sender_name="Sarah Johnson",
        sender_address="45 Smith Street, Melbourne VIC 3000",
        recipient_name="Michael Chen",
        recipient_address="123 George Street, Sydney NSW 2000",
        recipient_phone="+61412345678",
        recipient_email="michael.chen@example.com",
        service_type="standard",
        weight_kg=0.5,
        dimensions_cm="20x15x10",
        declared_value=25.00,
        store_location=distribution_centers[0]
    )
    parcel1["fraud_risk_score"] = 5.0
    parcel1["origin_location"] = distribution_centers[0]
    parcel1["current_status"] = "At Depot"
    await db.parcels_container_client.upsert_item(parcel1)
    
    request1 = await db.request_approval(
        parcel_barcode=parcel1["barcode"],
        request_type="delivery_confirmation",
        description="Standard delivery confirmation - Verified sender",
        priority="low",
        requested_by="System",
        parcel_dc=distribution_centers[0],
        parcel_status="At Depot"
    )
    created_parcels["auto_approve"].append({
        "barcode": parcel1["barcode"],
        "reason": "Low fraud risk (5%) + low value ($25) + verified sender",
        "request_id": request1
    })
    
    # 2. Delivered status with confirmation
    parcel2 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}AB",
        sender_name="Emma Wilson",
        sender_address="78 Park Avenue, Brisbane QLD 4000",
        recipient_name="David Martinez",
        recipient_address="456 Collins Street, Melbourne VIC 3000",
        recipient_phone="+61423456789",
        recipient_email="david.martinez@example.com",
        service_type="express",
        weight_kg=1.2,
        dimensions_cm="30x20x15",
        declared_value=75.00,
        store_location=distribution_centers[1]
    )
    parcel2["fraud_risk_score"] = 8.0
    parcel2["origin_location"] = distribution_centers[1]
    parcel2["current_status"] = "Delivered"
    parcel2["is_delivered"] = True
    await db.parcels_container_client.upsert_item(parcel2)
    
    request2 = await db.request_approval(
        parcel_barcode=parcel2["barcode"],
        request_type="delivery_confirmation",
        description="Delivery confirmation for completed parcel",
        priority="low",
        requested_by="Driver D001",
        parcel_dc=distribution_centers[1],
        parcel_status="Delivered"
    )
    created_parcels["auto_approve"].append({
        "barcode": parcel2["barcode"],
        "reason": "Delivered status + delivery_confirmation type",
        "request_id": request2
    })
    
    # 3. Verified recipient with low risk
    parcel3 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}AC",
        sender_name="Tech Supplies Co",
        sender_address="100 Business Park Drive, Sydney NSW 2000",
        recipient_name="Alice Thompson",
        recipient_address="789 Queen Street, Brisbane QLD 4000",
        recipient_phone="+61434567890",
        recipient_email="alice.thompson@example.com",
        service_type="overnight",
        weight_kg=2.0,
        dimensions_cm="40x30x20",
        declared_value=95.00,
        store_location=distribution_centers[2]
    )
    parcel3["fraud_risk_score"] = 3.0
    parcel3["origin_location"] = distribution_centers[2]
    parcel3["current_status"] = "At Depot"
    await db.parcels_container_client.upsert_item(parcel3)
    
    request3 = await db.request_approval(
        parcel_barcode=parcel3["barcode"],
        request_type="delivery_redirect",
        description="Address update requested - Verified recipient contacted us directly",
        priority="medium",
        requested_by="Customer Service",
        parcel_dc=distribution_centers[2],
        parcel_status="At Depot"
    )
    created_parcels["auto_approve"].append({
        "barcode": parcel3["barcode"],
        "reason": "Verified recipient + low fraud risk (3%)",
        "request_id": request3
    })
    
    print(f"   ✅ Created {len(created_parcels['auto_approve'])} auto-approve parcels")
    
    # ==================== AUTO-DENY SCENARIOS ====================
    print("\n❌ Creating AUTO-DENY parcels...")
    
    # 1. High fraud risk
    parcel4 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}DA",
        sender_name="Suspicious Sender",
        sender_address="Unknown Location, Sydney NSW 2000",
        recipient_name="John Doe",
        recipient_address="10 Collins Street, Melbourne VIC 3000",
        recipient_phone="+61400000000",
        recipient_email="fake@suspicious.com",
        service_type="overnight",
        weight_kg=5.0,
        dimensions_cm="50x40x30",
        declared_value=1500.00,
        store_location=distribution_centers[3]
    )
    parcel4["fraud_risk_score"] = 85.0
    parcel4["origin_location"] = distribution_centers[3]
    parcel4["current_status"] = "At Depot"
    await db.parcels_container_client.upsert_item(parcel4)
    
    request4 = await db.request_approval(
        parcel_barcode=parcel4["barcode"],
        request_type="exception_handling",
        description="Multiple delivery address changes requested in short time",
        priority="high",
        requested_by="Security Team",
        parcel_dc=distribution_centers[3],
        parcel_status="At Depot"
    )
    created_parcels["auto_deny"].append({
        "barcode": parcel4["barcode"],
        "reason": "High fraud risk score (85%)",
        "request_id": request4
    })
    
    # 2. Blacklisted address
    parcel5 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}DB",
        sender_name="Generic Company",
        sender_address="555 Business Road, Perth WA 6000",
        recipient_name="Robert Brown",
        recipient_address="999 Known Fraud Street, Adelaide SA 5000",
        recipient_phone="+61445678901",
        recipient_email="robert.brown@example.com",
        service_type="standard",
        weight_kg=1.0,
        dimensions_cm="25x20x10",
        declared_value=200.00,
        store_location=distribution_centers[4]
    )
    parcel5["fraud_risk_score"] = 45.0
    parcel5["origin_location"] = distribution_centers[4]
    parcel5["current_status"] = "At Depot"
    await db.parcels_container_client.upsert_item(parcel5)
    
    request5 = await db.request_approval(
        parcel_barcode=parcel5["barcode"],
        request_type="delivery_redirect",
        description="Delivery to blacklist address - multiple previous fraud incidents",
        priority="critical",
        requested_by="Depot Manager",
        parcel_dc=distribution_centers[4],
        parcel_status="At Depot"
    )
    created_parcels["auto_deny"].append({
        "barcode": parcel5["barcode"],
        "reason": "Blacklisted address detected",
        "request_id": request5
    })
    
    # 3. Duplicate request (suspicious)
    parcel6 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}DC",
        sender_name="Online Retailer Ltd",
        sender_address="200 Commerce Street, Canberra ACT 2600",
        recipient_name="Lisa Anderson",
        recipient_address="321 Main Road, Sydney NSW 2000",
        recipient_phone="+61456789012",
        recipient_email="lisa.anderson@example.com",
        service_type="express",
        weight_kg=0.8,
        dimensions_cm="20x15x8",
        declared_value=150.00,
        store_location=distribution_centers[5]
    )
    parcel6["fraud_risk_score"] = 35.0
    parcel6["origin_location"] = distribution_centers[5]
    parcel6["current_status"] = "In Transit"
    await db.parcels_container_client.upsert_item(parcel6)
    
    request6 = await db.request_approval(
        parcel_barcode=parcel6["barcode"],
        request_type="delivery_redirect",
        description="Duplicate address change request - already processed twice today",
        priority="high",
        requested_by="System",
        parcel_dc=distribution_centers[5],
        parcel_status="In Transit"
    )
    created_parcels["auto_deny"].append({
        "barcode": parcel6["barcode"],
        "reason": "Duplicate request detected",
        "request_id": request6
    })
    
    # 4. Missing documentation
    parcel7 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}DD",
        sender_name="Import Export Company",
        sender_address="88 Port Road, Adelaide SA 5000",
        recipient_name="James Wilson",
        recipient_address="567 Beach Road, Gold Coast QLD 4217",
        recipient_phone="+61467890123",
        recipient_email="james.wilson@example.com",
        service_type="registered",
        weight_kg=10.0,
        dimensions_cm="60x50x40",
        declared_value=3000.00,
        store_location=distribution_centers[6]
    )
    parcel7["fraud_risk_score"] = 25.0
    parcel7["origin_location"] = distribution_centers[6]
    parcel7["current_status"] = "At Depot"
    await db.parcels_container_client.upsert_item(parcel7)
    
    request7 = await db.request_approval(
        parcel_barcode=parcel7["barcode"],
        request_type="damage_claim",
        description="Damage claim missing required photos and customs documentation",
        priority="medium",
        requested_by="Claims Department",
        parcel_dc=distribution_centers[6],
        parcel_status="At Depot"
    )
    created_parcels["auto_deny"].append({
        "barcode": parcel7["barcode"],
        "reason": "Missing required documentation",
        "request_id": request7
    })
    
    print(f"   ❌ Created {len(created_parcels['auto_deny'])} auto-deny parcels")
    
    # ==================== MANUAL REVIEW SCENARIOS ====================
    print("\n⚠️  Creating MANUAL REVIEW parcels...")
    
    # 1. Medium fraud risk + high value (requires human judgment)
    parcel8 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}MA",
        sender_name="Electronics Warehouse",
        sender_address="150 Tech Park, Melbourne VIC 3000",
        recipient_name="Patricia Davis",
        recipient_address="789 Residential Street, Perth WA 6000",
        recipient_phone="+61478901234",
        recipient_email="patricia.davis@example.com",
        service_type="express",
        weight_kg=3.5,
        dimensions_cm="45x35x25",
        declared_value=2500.00,
        store_location=distribution_centers[7]
    )
    parcel8["fraud_risk_score"] = 45.0
    parcel8["origin_location"] = distribution_centers[7]
    parcel8["current_status"] = "At Depot"
    await db.parcels_container_client.upsert_item(parcel8)
    
    request8 = await db.request_approval(
        parcel_barcode=parcel8["barcode"],
        request_type="exception_handling",
        description="High value electronics - recipient requests alternative delivery location",
        priority="high",
        requested_by="Customer Service",
        parcel_dc=distribution_centers[7],
        parcel_status="At Depot"
    )
    created_parcels["manual_review"].append({
        "barcode": parcel8["barcode"],
        "reason": "Medium fraud risk (45%) + high value ($2500) - needs human review",
        "request_id": request8
    })
    
    # 2. Complex delivery situation
    parcel9 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}MB",
        sender_name="Medical Supplies Pty Ltd",
        sender_address="22 Health Drive, Brisbane QLD 4000",
        recipient_name="Dr. Thomas Lee",
        recipient_address="456 Hospital Road, Sydney NSW 2000",
        recipient_phone="+61489012345",
        recipient_email="thomas.lee@hospital.com.au",
        service_type="overnight",
        weight_kg=2.5,
        dimensions_cm="35x30x20",
        declared_value=1200.00,
        store_location=distribution_centers[0]
    )
    parcel9["fraud_risk_score"] = 12.0
    parcel9["origin_location"] = distribution_centers[0]
    parcel9["current_status"] = "In Transit"
    await db.parcels_container_client.upsert_item(parcel9)
    
    request9 = await db.request_approval(
        parcel_barcode=parcel9["barcode"],
        request_type="delivery_redirect",
        description="Time-sensitive medical supplies - recipient traveling, requests delivery to clinic instead of hospital",
        priority="critical",
        requested_by="Medical Team",
        parcel_dc=distribution_centers[0],
        parcel_status="In Transit"
    )
    created_parcels["manual_review"].append({
        "barcode": parcel9["barcode"],
        "reason": "Time-sensitive medical delivery with location change - needs approval",
        "request_id": request9
    })
    
    # 3. Borderline fraud risk with unusual circumstances
    parcel10 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}MC",
        sender_name="Private Seller",
        sender_address="Private Residence, Adelaide SA 5000",
        recipient_name="Jennifer Taylor",
        recipient_address="12 Apartment Block, Darwin NT 0800",
        recipient_phone="+61490123456",
        recipient_email="jennifer.taylor@example.com",
        service_type="registered",
        weight_kg=1.5,
        dimensions_cm="30x25x15",
        declared_value=800.00,
        store_location=distribution_centers[1]
    )
    parcel10["fraud_risk_score"] = 38.0
    parcel10["origin_location"] = distribution_centers[1]
    parcel10["current_status"] = "At Depot"
    await db.parcels_container_client.upsert_item(parcel10)
    
    request10 = await db.request_approval(
        parcel_barcode=parcel10["barcode"],
        request_type="return_to_sender",
        description="Recipient claims never ordered - private sale dispute, sender wants parcel held pending investigation",
        priority="medium",
        requested_by="Customer Service",
        parcel_dc=distribution_centers[1],
        parcel_status="At Depot"
    )
    created_parcels["manual_review"].append({
        "barcode": parcel10["barcode"],
        "reason": "Purchase dispute between private parties - requires investigation",
        "request_id": request10
    })
    
    # 4. Lost package claim - needs verification
    parcel11 = await db.register_parcel(
        barcode=f"AP{str(uuid.uuid4())[:8].upper()}MD",
        sender_name="Fashion Boutique",
        sender_address="300 Shopping Plaza, Sydney NSW 2000",
        recipient_name="Michelle Garcia",
        recipient_address="678 Suburb Street, Hobart TAS 7000",
        recipient_phone="+61401234567",
        recipient_email="michelle.garcia@example.com",
        service_type="standard",
        weight_kg=0.6,
        dimensions_cm="30x25x10",
        declared_value=450.00,
        store_location=distribution_centers[2]
    )
    parcel11["fraud_risk_score"] = 22.0
    parcel11["origin_location"] = distribution_centers[2]
    parcel11["current_status"] = "In Transit"
    await db.parcels_container_client.upsert_item(parcel11)
    
    request11 = await db.request_approval(
        parcel_barcode=parcel11["barcode"],
        request_type="lost_package",
        description="Recipient claims package not received after 10 days, tracking shows delivered to mail room",
        priority="high",
        requested_by="Claims Department",
        parcel_dc=distribution_centers[2],
        parcel_status="In Transit"
    )
    created_parcels["manual_review"].append({
        "barcode": parcel11["barcode"],
        "reason": "Lost package claim conflicts with tracking - needs investigation",
        "request_id": request11
    })
    
    print(f"   ⚠️  Created {len(created_parcels['manual_review'])} manual review parcels")
    
    # ==================== SUMMARY ====================
    print("\n" + "=" * 60)
    print("✅ Approval Demo Parcels Created Successfully!")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   ✅ Auto-Approve: {len(created_parcels['auto_approve'])} parcels")
    print(f"      - Low risk + low value")
    print(f"      - Delivered + confirmation")
    print(f"      - Verified sender/recipient")
    print(f"\n   ❌ Auto-Deny: {len(created_parcels['auto_deny'])} parcels")
    print(f"      - High fraud risk (>70%)")
    print(f"      - Blacklisted addresses")
    print(f"      - Duplicate requests")
    print(f"      - Missing documentation")
    print(f"\n   ⚠️  Manual Review: {len(created_parcels['manual_review'])} parcels")
    print(f"      - Medium fraud risk + high value")
    print(f"      - Complex delivery situations")
    print(f"      - Disputes requiring investigation")
    print(f"      - Claims needing verification")
    
    print(f"\n💡 Demo Instructions:")
    print(f"   1. Navigate to the Approvals page in the web app")
    print(f"   2. Enable 'Agent Mode' with your desired settings")
    print(f"   3. Click 'Process with AI Agent' to see automated decisions")
    print(f"   4. Observe how the agent auto-approves, auto-denies, or flags for manual review")
    
    return created_parcels


async def generate_test_data(num_parcels: int = 30, num_approvals: int = 10):
    """
    Generate test parcels and approval requests

    Args:
        num_parcels: Number of test parcels to generate (default: 30)
        num_approvals: Number of approval requests to generate (default: 10)
    """
    print("=" * 60)
    print("Zava - Test Data Generator")
    print("=" * 60)

    # Check environment variables
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    key = os.getenv("COSMOS_DB_KEY")

    if not endpoint or not key:
        print("\n❌ ERROR: COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables must be set")
        print("Please update your .env file with your Cosmos DB credentials")
        return False

    print(f"\n📊 Configuration:")
    print(f"   Cosmos DB Endpoint: {endpoint}")
    print(f"   Database Name: {os.getenv('COSMOS_DB_DATABASE_NAME', 'agent_workflow_db')}")
    print(f"   Parcels to generate: {num_parcels}")
    print(f"   Approval requests to generate: {num_approvals}")

    try:
        async with ParcelTrackingDB() as db:
            # Generate test parcels
            print(f"\n📦 Generating {num_parcels} Test Parcels...")
            test_parcels = await db.add_random_test_parcels(num_parcels)
            print(f"✅ Added {len(test_parcels)} test parcels")

            # Verify distribution centers are assigned correctly based on status
            # Valid DC values: actual DC codes, 'To Be Advised', 'Completed', 'Unknown DC'
            parcels_with_issues = []
            for p in test_parcels:
                dc = p.get("origin_location", "N/A")
                status = p.get("current_status", "unknown")

                # Check for unexpected DC assignments
                if status == "Registered" and dc != "To Be Advised":
                    parcels_with_issues.append(f"{p['barcode']}: Registered should have 'To Be Advised' but has '{dc}'")
                elif status in ["Out for Delivery", "Delivered"] and dc != "Completed":
                    parcels_with_issues.append(f"{p['barcode']}: {status} should have 'Completed' but has '{dc}'")
                elif status == "Collected" and dc != "Unknown DC":
                    parcels_with_issues.append(f"{p['barcode']}: Collected should have 'Unknown DC' but has '{dc}'")
                elif status in ["At Depot", "Sorting", "In Transit"] and dc in [
                    "To Be Advised",
                    "Completed",
                    "Unknown DC",
                ]:
                    parcels_with_issues.append(f"{p['barcode']}: {status} should have actual DC but has '{dc}'")

            if parcels_with_issues:
                print(f"⚠️  Warning: {len(parcels_with_issues)} parcels have incorrect DC assignments")
                for issue in parcels_with_issues[:3]:  # Show first 3 issues
                    print(f"      - {issue}")

            # Display sample parcels
            print("\n📋 Sample Parcels:")
            for i, parcel in enumerate(test_parcels[:5], 1):
                dc = parcel.get("origin_location", "N/A")
                print(f"   {i}. {parcel['barcode']}")
                print(f"      → To: {parcel['recipient_name']} ({parcel['destination_postcode']})")
                print(f"      → Service: {parcel['service_type']} | Status: {parcel['current_status']}")
                print(f"      → DC: {dc}")

            if len(test_parcels) > 5:
                print(f"   ... and {len(test_parcels) - 5} more parcels")

            # Distribution center statistics
            dc_count = {}
            status_by_dc = {}
            for parcel in test_parcels:
                dc = parcel.get("origin_location", "Unknown DC")
                status = parcel.get("current_status", "unknown")
                dc_count[dc] = dc_count.get(dc, 0) + 1
                if dc not in status_by_dc:
                    status_by_dc[dc] = []
                status_by_dc[dc].append(status)

            print(f"\n📍 Distribution Center Coverage:")
            print(
                f"   Total DCs used: {len([dc for dc in dc_count.keys() if dc not in ['Unknown DC', 'To Be Advised', 'Completed']])}"
            )

            # Show special DC statuses
            for special_dc in ["To Be Advised", "Unknown DC", "Completed"]:
                if special_dc in dc_count:
                    statuses = status_by_dc.get(special_dc, [])
                    print(f"   ℹ️  Parcels with '{special_dc}': {dc_count[special_dc]}")
                    # Show breakdown by status
                    status_counts = {}
                    for status in statuses:
                        status_counts[status] = status_counts.get(status, 0) + 1
                    for status, count in status_counts.items():
                        # Validate correctness
                        if special_dc == "To Be Advised":
                            valid = "✓" if status == "Registered" else "⚠️"
                        elif special_dc == "Completed":
                            valid = "✓" if status in ["Out for Delivery", "Delivered"] else "⚠️"
                        elif special_dc == "Unknown DC":
                            valid = "✓" if status == "Collected" else "⚠️"
                        else:
                            valid = "?"
                        print(f"      {valid} {status}: {count}")

            # Generate approval requests
            print(f"\n📝 Adding {num_approvals} Test Approval Requests...")
            approval_requests = await db.add_random_approval_requests(num_approvals)
            print(f"✅ Added {len(approval_requests)} approval requests")

            # Display sample approvals
            pending = await db.get_all_pending_approvals()
            print("\n📋 Sample Approval Requests:")
            for i, approval in enumerate(pending[:5], 1):
                dc = approval.get("parcel_dc", "N/A")
                print(f"   {i}. {approval['id']}")
                print(f"      → Type: {approval['request_type']} | Priority: {approval['priority']}")
                print(f"      → Parcel: {approval['parcel_barcode']}")
                print(f"      → DC: {dc} | Status: {approval.get('parcel_status', 'N/A')}")

            if len(pending) > 5:
                print(f"   ... and {len(pending) - 5} more approval requests")

            # Initialize company information if needed
            print("\n🏢 Checking Company Information...")
            company_info = await db.get_latest_company_info("company_profile")
            if not company_info:
                print("   ℹ️  No company information found. Initializing...")
                await initialize_company_information()
            else:
                print("   ✅ Company information already exists")

            print("\n" + "=" * 60)
            print("✅ Test Data Generation Complete!")
            print("=" * 60)
            print(f"\nSummary:")
            print(f"  • {len(test_parcels)} parcels created")
            print(f"  • {len(approval_requests)} approval requests created")
            print(f"  • Distribution centers: 40 locations across Australia")
            print(
                f"  • Status types: Registered, Collected, At Depot, Sorting, In Transit, Out for Delivery, Delivered"
            )
            print(f"\nYou can now use these test parcels in the Zava application.")

            return True

    except Exception as e:
        print(f"\n❌ Error generating test data: {e}")
        import traceback

        traceback.print_exc()
        return False


async def cleanup_approval_requests():
    """Clean up only approval requests from the database"""
    print("\n⚠️  WARNING: This will delete ALL approval requests!")
    confirm = input("Type 'YES' to confirm: ")

    if confirm != "YES":
        print("❌ Cleanup cancelled")
        return False

    print("\n🗑️  Cleaning up approval requests...")
    try:
        async with ParcelTrackingDB() as db:
            await db.cleanup_approval_requests()
            print("✅ Approval requests cleaned up successfully")
            return True
    except Exception as e:
        print(f"❌ Error cleaning up approval requests: {e}")
        return False


async def cleanup_test_data():
    """Clean up all test data from the database"""
    print("\n⚠️  WARNING: This will delete ALL data from the database!")
    confirm = input("Type 'DELETE ALL' to confirm: ")

    if confirm != "DELETE ALL":
        print("❌ Cleanup cancelled")
        return False

    print("\n🗑️  Cleaning up database...")
    try:
        async with ParcelTrackingDB() as db:
            await db.cleanup_database(confirm=True)
            print("✅ Database cleaned up successfully")
            return True
    except Exception as e:
        print(f"❌ Error cleaning up database: {e}")
        return False


async def main():
    """Main function with interactive menu"""
    print("\n" + "=" * 60)
    print("Zava - SAMPLE DATA GENERATOR")
    print("=" * 60)

    while True:
        print("\n📋 Options:")
        print("  1. Generate test data (30 parcels + 10 approvals)")
        print("  2. Generate custom amount of test data")
        print("  3. Generate APPROVAL DEMO parcels (for Agent Mode demonstration)")
        print("  4. Delete only approval requests")
        print("  5. Delete all test data")
        print("  6. Exit")

        choice = input("\n👉 Enter your choice (1-6): ").strip()

        if choice == "1":
            await generate_test_data(30, 10)
        elif choice == "2":
            try:
                num_parcels = int(input("Number of parcels to generate: ").strip())
                num_approvals = int(input("Number of approval requests to generate: ").strip())
                await generate_test_data(num_parcels, num_approvals)
            except ValueError:
                print("❌ Invalid input. Please enter numbers only.")
        elif choice == "3":
            try:
                async with ParcelTrackingDB() as db:
                    await generate_approval_demo_parcels(db)
            except Exception as e:
                print(f"❌ Error generating approval demo parcels: {e}")
                import traceback
                traceback.print_exc()
        elif choice == "4":
            await cleanup_approval_requests()
        elif choice == "5":
            await cleanup_test_data()
        elif choice == "6":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
