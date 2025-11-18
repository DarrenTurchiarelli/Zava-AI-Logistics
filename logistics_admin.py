# logistics_admin.py
# Data & Administration Features

import asyncio
import os
from parcel_tracking_db import ParcelTrackingDB

async def bulk_import_parcels():
    """Bulk import parcels from CSV or API"""
    print("\n=== Bulk Import Parcels ===")
    
    print("📥 Bulk import options:")
    print("  1. CSV file upload")
    print("  2. API integration")
    print("  3. Excel spreadsheet")
    print("  4. Generate sample bulk data")
    
    choice = input("Select import method (1-4): ").strip()
    
    if choice == "1":
        filename = input("Enter CSV filename: ") or "parcels_bulk.csv"
        print(f"📄 Processing CSV file: {filename}")
        print("🔍 Validating data format...")
        
        # Simulate CSV processing
        await asyncio.sleep(1)
        print("✅ CSV validation completed")
        print("📊 Import summary:")
        print("  📦 Total records: 247")
        print("  ✅ Valid records: 243")
        print("  ❌ Invalid records: 4")
        print("  🔄 Duplicate tracking numbers: 2")
        
    elif choice == "2":
        api_endpoint = input("API endpoint: ") or "https://api.warehouse.com/parcels"
        print(f"🌐 Connecting to API: {api_endpoint}")
        print("🔑 Authenticating...")
        await asyncio.sleep(1)
        print("✅ API connection established")
        print("📡 Fetching parcel data...")
        await asyncio.sleep(1)
        print("📊 API import completed: 156 parcels imported")
        
    elif choice == "4":
        count = int(input("Generate how many sample parcels? [50]: ") or "50")
        print(f"🎲 Generating {count} sample parcels...")
        
        async with ParcelTrackingDB() as db:
            parcels = await db.add_random_test_parcels(count)
            print(f"✅ Generated {len(parcels)} parcels successfully")

async def export_manifests():
    """Export delivery manifests and reports"""
    print("\n=== Export Manifests ===")
    
    print("📤 Export options:")
    print("  1. Daily delivery manifest")
    print("  2. Route optimization report")
    print("  3. Performance analytics")
    print("  4. Custom date range export")
    
    choice = input("Select export type (1-4): ").strip()
    
    if choice == "1":
        date = input("Enter date (YYYY-MM-DD) or press Enter for today: ") or "2025-11-18"
        print(f"📋 Generating daily manifest for {date}")
        
        # Simulate manifest generation
        await asyncio.sleep(1)
        
        print("✅ Manifest generated successfully")
        print("📊 Export summary:")
        print(f"  📅 Date: {date}")
        print("  🚛 Routes: 12")
        print("  📦 Total parcels: 847")
        print("  👥 Drivers assigned: 15")
        print(f"  📄 File: daily_manifest_{date}.pdf")
        
    elif choice == "2":
        route_id = input("Route ID (or 'all' for all routes): ") or "all"
        print(f"🗺️ Generating route optimization report for {route_id}")
        await asyncio.sleep(1)
        print("✅ Route optimization report generated")
        print("  📊 Efficiency gains: 15%")
        print("  ⛽ Fuel savings: $127.50")
        print("  🌱 CO₂ reduction: 47kg")
        
    elif choice == "3":
        print("📈 Generating performance analytics...")
        await asyncio.sleep(1)
        print("✅ Analytics export completed:")
        print("  📊 KPI dashboard: performance_kpi.xlsx")
        print("  📈 Trend analysis: trends_analysis.pdf")
        print("  💰 Cost breakdown: cost_analysis.csv")

async def rbac_audit():
    """Role-based access control and audit management"""
    print("\n=== RBAC & Audit Management ===")
    
    print("🔑 Available roles:")
    roles = [
        {"role": "Customer Service", "users": 12, "permissions": "Read parcels, Update status, Customer comms"},
        {"role": "Driver", "users": 25, "permissions": "Scan parcels, Update location, Proof of delivery"},
        {"role": "Depot Supervisor", "users": 5, "permissions": "Manage routes, Approve exceptions, View analytics"},
        {"role": "Operations Manager", "users": 3, "permissions": "Full system access, User management, Analytics"},
        {"role": "Customer", "users": 1247, "permissions": "Track parcels, Update preferences, Feedback"}
    ]
    
    print("👥 Current role assignments:")
    for role_data in roles:
        print(f"  🔐 {role_data['role']}: {role_data['users']} users")
        print(f"     📋 Permissions: {role_data['permissions']}")
    
    print("\n📋 Audit trail options:")
    print("  1. View recent activity log")
    print("  2. Generate compliance report")
    print("  3. User access review")
    print("  4. Permission changes audit")
    
    audit_choice = input("Select audit option (1-4): ").strip()
    
    if audit_choice == "1":
        print("\n📅 Recent Activity Log (Last 24 hours):")
        activities = [
            {"time": "14:32", "user": "driver.john", "action": "Parcel scan", "resource": "LP123456"},
            {"time": "14:25", "user": "cs.sarah", "action": "Status update", "resource": "Customer inquiry"},
            {"time": "14:18", "user": "supervisor.mike", "action": "Route approval", "resource": "RT-MEL-001"},
            {"time": "14:12", "user": "manager.lisa", "action": "User role change", "resource": "driver.new"},
        ]
        
        for activity in activities:
            print(f"  🕐 {activity['time']} | {activity['user']} | {activity['action']} | {activity['resource']}")
    
    elif audit_choice == "2":
        print("\n📋 Generating compliance report...")
        await asyncio.sleep(1)
        print("✅ Compliance report generated:")
        print("  🔒 Data access compliance: 98.5%")
        print("  👥 User permission reviews: Up to date")
        print("  📊 Audit trail completeness: 100%")
        print("  🔐 Failed login attempts: 3 (all blocked)")

async def synthetic_scenario_builder():
    """Generate realistic test scenarios for training and testing"""
    print("\n=== Synthetic Scenario Builder ===")
    
    print("🧪 Scenario generation options:")
    print("  1. Melbourne metro delivery routes")
    print("  2. Weather impact scenarios")
    print("  3. Peak period simulations")
    print("  4. Customer behavior patterns")
    print("  5. Vehicle breakdown scenarios")
    
    choice = input("Select scenario type (1-5): ").strip()
    
    if choice == "1":
        print("🗺️ Generating Melbourne metro scenarios...")
        suburb_count = int(input("Number of suburbs to include [10]: ") or "10")
        parcel_density = input("Parcel density (low/medium/high) [medium]: ") or "medium"
        
        melbourne_suburbs = [
            "Carlton", "Fitzroy", "South Yarra", "Prahran", "Richmond", 
            "Collingwood", "Brunswick", "Northcote", "Hawthorn", "St Kilda"
        ]
        
        print(f"✅ Generated scenario: {suburb_count} suburbs, {parcel_density} density")
        print("📊 Scenario parameters:")
        print(f"  📍 Coverage area: {', '.join(melbourne_suburbs[:suburb_count])}")
        print(f"  📦 Estimated parcels: {suburb_count * (50 if parcel_density == 'medium' else 30 if parcel_density == 'low' else 80)}")
        print(f"  🚛 Recommended vehicles: {max(2, suburb_count // 3)}")
        
    elif choice == "2":
        print("🌤️ Generating weather impact scenarios...")
        weather_type = input("Weather type (rain/storm/heat/normal) [rain]: ") or "rain"
        severity = input("Severity (mild/moderate/severe) [moderate]: ") or "moderate"
        
        impact_factors = {
            "rain": {"delivery_delay": "15%", "capacity_reduction": "10%"},
            "storm": {"delivery_delay": "45%", "capacity_reduction": "30%"},
            "heat": {"delivery_delay": "20%", "capacity_reduction": "5%"},
            "normal": {"delivery_delay": "0%", "capacity_reduction": "0%"}
        }
        
        factors = impact_factors[weather_type]
        print(f"🌦️ Weather scenario: {weather_type.title()} ({severity})")
        print(f"  ⏰ Delivery time impact: +{factors['delivery_delay']}")
        print(f"  📦 Capacity reduction: {factors['capacity_reduction']}")
        print(f"  🚛 Alternative strategies: Indoor deliveries priority, parcel locker redirection")
    
    elif choice == "3":
        print("📈 Generating peak period simulation...")
        period = input("Peak period (christmas/blackfriday/normal) [christmas]: ") or "christmas"
        
        multipliers = {
            "christmas": 3.5,
            "blackfriday": 4.2,
            "normal": 1.0
        }
        
        base_volume = 1000
        peak_volume = int(base_volume * multipliers[period])
        
        print(f"🎄 Peak period: {period.title()}")
        print(f"📊 Volume increase: {peak_volume} parcels ({multipliers[period]}x normal)")
        print(f"👥 Additional staff required: {int(multipliers[period] * 10)}")
        print(f"🚛 Extra vehicles needed: {int(multipliers[period] * 3)}")
        print(f"⏰ Extended operating hours: {6 + int(multipliers[period])}AM - {6 + int(multipliers[period])}PM")

async def view_pending_approvals():
    """View and manage pending approvals from the approval system"""
    print("\n=== View & Manage Pending Approvals ===")
    
    async with ParcelTrackingDB() as db:
        try:
            # Use the proper method to get pending approvals
            approvals = await db.get_all_pending_approvals()
            
            if not approvals:
                print("✅ No pending approvals found")
                return
            
            print(f"📋 Found {len(approvals)} pending approvals:")
            print("=" * 70)
            
            # Display approvals with numbering for easy selection
            for i, approval in enumerate(approvals, 1):
                print(f"\n#{i} 🆔 ID: {approval['id']}")
                print(f"    📦 Parcel: {approval.get('parcel_barcode', 'N/A')}")
                print(f"    🎯 Type: {approval.get('approval_type', 'N/A')}")
                print(f"    ⏰ Requested: {approval.get('timestamp', 'N/A')}")
                print(f"    👤 Requester: {approval.get('requester_name', 'N/A')}")
                print(f"    📝 Reason: {approval.get('reason', 'N/A')}")
                if i < len(approvals):
                    print("    " + "-" * 50)
            
            print("\n" + "=" * 70)
            print("🔧 Management Options:")
            print("  • Enter approval number to approve/reject (1-{})".format(len(approvals)))
            print("  • Enter 'id:' followed by approval ID (e.g., id:f997bbc3-dd0e-4624-8206-1fb7c71f3965)")
            print("  • Enter 'parcel:' followed by parcel barcode (e.g., parcel:LP944204)")
            print("  • Enter 'refresh' or 'r' to refresh list")
            print("  • Enter 'quit' or 'q' to return to main menu")
            
            while True:
                choice = input(f"\n👉 Select approval to manage (1-{len(approvals)}, id:xxx, parcel:xxx, refresh/r, quit/q): ").strip()
                
                if choice.lower() in ['q', 'quit']:
                    break
                elif choice.lower() in ['r', 'refresh']:
                    # Refresh and restart
                    await view_pending_approvals()
                    return
                elif choice.lower().startswith('id:'):
                    # Manual ID input
                    approval_id = choice[3:].strip()
                    selected_approval = await find_approval_by_id(db, approval_id, approvals)
                    if selected_approval:
                        await process_approval_decision(db, selected_approval)
                    else:
                        print(f"❌ Approval ID '{approval_id}' not found in pending approvals.")
                elif choice.lower().startswith('parcel:'):
                    # Manual parcel barcode input
                    parcel_barcode = choice[7:].strip()
                    selected_approval = find_approval_by_parcel(parcel_barcode, approvals)
                    if selected_approval:
                        await process_approval_decision(db, selected_approval)
                    else:
                        print(f"❌ No pending approval found for parcel '{parcel_barcode}'.")
                else:
                    try:
                        approval_index = int(choice) - 1
                        if 0 <= approval_index < len(approvals):
                            selected_approval = approvals[approval_index]
                            await process_approval_decision(db, selected_approval)
                        else:
                            print("❌ Invalid approval number. Please try again.")
                    except ValueError:
                        print("❌ Invalid input. Use: number, id:xxx, parcel:xxx, 'refresh'/'r', or 'quit'/'q'.")
                
        except Exception as e:
            print(f"❌ Error retrieving approvals: {e}")

async def find_approval_by_id(db, approval_id, approvals_list):
    """Find approval by exact ID match"""
    # First check in current list (faster)
    for approval in approvals_list:
        if approval['id'] == approval_id:
            return approval
    
    # If not found in current list, check database directly
    try:
        approval = await db.get_approval_status(approval_id)
        if approval and approval.get('status') == 'pending':
            return approval
    except Exception as e:
        print(f"❌ Error looking up approval ID: {e}")
    
    return None

def find_approval_by_parcel(parcel_barcode, approvals_list):
    """Find approval by parcel barcode"""
    matching_approvals = []
    
    for approval in approvals_list:
        approval_parcel = approval.get('parcel_barcode', '').strip().upper()
        search_parcel = parcel_barcode.strip().upper()
        
        if approval_parcel == search_parcel:
            matching_approvals.append(approval)
    
    if len(matching_approvals) == 1:
        return matching_approvals[0]
    elif len(matching_approvals) > 1:
        print(f"⚠️ Multiple approvals found for parcel '{parcel_barcode}':")
        for i, approval in enumerate(matching_approvals, 1):
            print(f"  {i}. ID: {approval['id'][:8]}... Type: {approval.get('approval_type', 'N/A')}")
        
        try:
            choice = input(f"Select which approval (1-{len(matching_approvals)}): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(matching_approvals):
                return matching_approvals[index]
            else:
                print("❌ Invalid selection.")
        except ValueError:
            print("❌ Invalid input.")
    
    return None

async def process_approval_decision(db, approval):
    """Process approval decision for a specific approval request"""
    print(f"\n📋 Managing Approval Request:")
    print(f"🆔 ID: {approval['id']}")
    print(f"📦 Parcel: {approval.get('parcel_barcode', 'N/A')}")
    print(f"🎯 Type: {approval.get('approval_type', 'N/A')}")
    print(f"📝 Reason: {approval.get('reason', 'N/A')}")
    
    print("\n🎯 Decision Options:")
    print("  1. ✅ Approve request")
    print("  2. ❌ Reject request")
    print("  3. 🔙 Back to approval list")
    
    while True:
        decision = input("\n👉 Select action (1-3): ").strip()
        
        if decision == "3":
            return
        elif decision in ["1", "2"]:
            # Get supervisor details
            supervisor_name = input("Enter your supervisor name: ").strip() or "System Admin"
            comments = input("Enter comments (optional): ").strip()
            
            request_id = approval['id']
            
            if decision == "1":
                # Approve
                print(f"\n⏳ Approving request {request_id}...")
                success = await db.approve_request(request_id, supervisor_name, comments)
                if success:
                    print("✅ Request approved successfully!")
                    print(f"👤 Approved by: {supervisor_name}")
                    if comments:
                        print(f"💬 Comments: {comments}")
                else:
                    print("❌ Failed to approve request")
            
            elif decision == "2":
                # Reject
                print(f"\n⏳ Rejecting request {request_id}...")
                success = await db.reject_request(request_id, supervisor_name, comments)
                if success:
                    print("❌ Request rejected successfully!")
                    print(f"👤 Rejected by: {supervisor_name}")
                    if comments:
                        print(f"💬 Comments: {comments}")
                else:
                    print("❌ Failed to reject request")
            
            # Pause to show result
            input("\n⏸️ Press Enter to continue...")
            return
            
        else:
            print("❌ Invalid choice. Please select 1, 2, or 3.")