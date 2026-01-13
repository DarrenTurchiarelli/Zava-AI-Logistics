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

from parcel_tracking_db import ParcelTrackingDB, initialize_company_information


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
        print("  3. Delete only approval requests")
        print("  4. Delete all test data")
        print("  5. Exit")

        choice = input("\n👉 Enter your choice (1-5): ").strip()

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
            await cleanup_approval_requests()
        elif choice == "4":
            await cleanup_test_data()
        elif choice == "5":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
