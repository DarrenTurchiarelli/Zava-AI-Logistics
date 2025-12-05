# logistics_core.py
# Core parcel operations: register, view, track, scan, generate test data

import asyncio
from datetime import datetime
from parcel_tracking_db import ParcelTrackingDB
from logistics_common import generate_parcel_barcode, get_sample_parcels, get_australian_state_from_postcode
import subprocess
import sys

async def register_parcel_manually():
    """Register a new parcel with manual input"""
    print("\n=== Store Parcel Registration ===")
    print("Enter parcel details (or 'q' to quit):")
    
    async with ParcelTrackingDB() as db:
        while True:
            barcode = input("\nParcel barcode (or press Enter for auto-generated): ").strip()
            if barcode.lower() == 'q':
                break
            
            if not barcode:
                barcode = generate_parcel_barcode()
                print(f"Generated barcode: {barcode}")
            
            # Check if barcode already exists
            existing_parcel = await db.get_parcel_by_barcode(barcode)
            if existing_parcel:
                print(f"Warning: Parcel with barcode {barcode} already exists!")
                continue
            
            # Sender information
            print("\n--- Sender Information ---")
            sender_name = input("Sender name: ").strip()
            if not sender_name:
                print("Sender name is required!")
                continue
            
            sender_address = input("Sender address: ").strip()
            if not sender_address:
                print("Sender address is required!")
                continue
            
            sender_phone = input("Sender phone [optional]: ").strip() or None
            
            # Recipient information
            print("\n--- Recipient Information ---")
            recipient_name = input("Recipient name: ").strip()
            if not recipient_name:
                print("Recipient name is required!")
                continue
            
            recipient_address = input("Recipient address: ").strip()
            if not recipient_address:
                print("Recipient address is required!")
                continue
            
            recipient_phone = input("Recipient phone [optional]: ").strip() or None
            
            destination_postcode = input("Destination postcode: ").strip()
            if not destination_postcode:
                print("Destination postcode is required!")
                continue
            
            # Auto-detect state from postcode using proper ranges
            suggested_state = get_australian_state_from_postcode(destination_postcode)
            
            destination_state = input(f"Destination state [auto-detected: {suggested_state}]: ").strip().upper()
            if not destination_state:
                destination_state = suggested_state
                print(f"Using auto-detected state: {destination_state}")
            
            # Service type
            print("\n--- Service Options ---")
            print("1. Standard (5 business days)")
            print("2. Express (2 business days)")
            print("3. Overnight (next business day)")
            print("4. Registered (3 business days with signature)")
            
            service_choice = input("Select service type [1-4, default 1]: ").strip() or "1"
            service_types = {
                '1': 'standard',
                '2': 'express', 
                '3': 'overnight',
                '4': 'registered'
            }
            service_type = service_types.get(service_choice, 'standard')
            
            # Optional details
            print("\n--- Optional Details ---")
            weight_input = input("Weight (kg) [optional]: ").strip()
            weight = float(weight_input) if weight_input else None
            
            dimensions = input("Dimensions (LxWxH cm) [optional]: ").strip() or None
            
            value_input = input("Declared value ($AUD) [optional]: ").strip()
            declared_value = float(value_input) if value_input else None
            
            print("\n--- Special Instructions ---")
            print("1. Temperature controlled - keep cool")
            print("2. Fragile - handle with care")
            print("3. Authority to leave if not home")
            print("4. Signature required")
            print("5. Call before delivery")
            print("6. Perishable goods - deliver by 5pm")
            print("7. Heavy item - 2 person lift required")
            print("8. Other (custom instructions)")
            print("9. None (no special instructions)")
            
            instruction_choice = input("Select special instructions [1-9, default 9]: ").strip() or "9"
            
            instruction_options = {
                '1': 'Temperature controlled - keep cool',
                '2': 'Fragile - handle with care',
                '3': 'Authority to leave if not home',
                '4': 'Signature required',
                '5': 'Call before delivery',
                '6': 'Perishable goods - deliver by 5pm',
                '7': 'Heavy item - 2 person lift required',
                '8': 'custom',
                '9': None
            }
            
            if instruction_choice == '8':
                special_instructions = input("Enter custom special instructions: ").strip() or None
            else:
                special_instructions = instruction_options.get(instruction_choice)
            
            store_location = input("Store location [default: Store_Default]: ").strip() or "Store_Default"
            
            # Register the parcel
            try:
                parcel = await db.register_parcel(
                    barcode=barcode,
                    sender_name=sender_name,
                    sender_address=sender_address,
                    sender_phone=sender_phone,
                    recipient_name=recipient_name,
                    recipient_address=recipient_address,
                    recipient_phone=recipient_phone,
                    destination_postcode=destination_postcode,
                    destination_state=destination_state,
                    service_type=service_type,
                    weight=weight,
                    dimensions=dimensions,
                    declared_value=declared_value,
                    special_instructions=special_instructions,
                    store_location=store_location
                )
                
                print(f"\n✅ Parcel registered successfully!")
                print(f"   📦 Barcode: {parcel['barcode']}")
                print(f"   🏷️  Tracking Number: {parcel['tracking_number']}")
                print(f"   📍 From: {sender_name} → {recipient_name}")
                print(f"   🚚 Service: {service_type.title()}")
                print(f"   🏪 Store: {store_location}")
                print(f"   📅 Estimated Delivery: {parcel['estimated_delivery'][:10]}")
                
            except Exception as e:
                print(f"❌ Error registering parcel: {e}")
            
            # Ask if user wants to register another
            another = input("\nRegister another parcel? (y/n): ").strip().lower()
            if another not in ['y', 'yes']:
                break

async def register_sample_parcels():
    """Register pre-defined sample parcels"""
    print("\n=== Registering Sample Parcels ===")
    
    async with ParcelTrackingDB() as db:
        sample_parcels = get_sample_parcels()
        registered_count = 0
        
        for sample in sample_parcels:
            barcode = generate_parcel_barcode()
            
            try:
                parcel = await db.register_parcel(
                    barcode=barcode,
                    sender_name=sample['sender_name'],
                    sender_address=sample['sender_address'],
                    sender_phone=sample.get('sender_phone'),
                    recipient_name=sample['recipient_name'],
                    recipient_address=sample['recipient_address'],
                    recipient_phone=sample.get('recipient_phone'),
                    destination_postcode=sample['destination_postcode'],
                    destination_state=sample['destination_state'],
                    service_type=sample['service_type'],
                    weight=sample.get('weight'),
                    dimensions=sample.get('dimensions'),
                    declared_value=sample.get('declared_value'),
                    special_instructions=sample.get('special_instructions'),
                    store_location=sample['store_location']
                )
                
                print(f"✅ Registered: {barcode} → {parcel['tracking_number']}")
                print(f"   {sample['sender_name']} → {sample['recipient_name']} ({sample['destination_postcode']})")
                registered_count += 1
                
            except Exception as e:
                print(f"❌ Error registering sample parcel: {e}")
        
        print(f"\n📊 Summary: {registered_count}/{len(sample_parcels)} sample parcels registered successfully")

async def view_all_parcels():
    """Display all registered parcels"""
    print("\n=== All Registered Parcels ===")
    
    async with ParcelTrackingDB() as db:
        parcels = await db.get_all_parcels()
        
        if not parcels:
            print("📭 No parcels found in the system.")
            print("💡 Tip: Use option 2 to register some sample parcels first.")
            return
        
        print(f"📦 Found {len(parcels)} parcels:\n")
        
        for i, parcel in enumerate(parcels, 1):
            print(f"{i}. 📦 {parcel['barcode']} | 🏷️ {parcel['tracking_number']}")
            print(f"   📍 {parcel['sender_name']} → {parcel['recipient_name']}")
            print(f"   🏪 {parcel['store_location']} | 🚚 {parcel['service_type'].title()}")
            print(f"   📊 {parcel['current_status'].title()} @ {parcel['current_location']}")
            if parcel.get('special_instructions'):
                print(f"   ⚠️  {parcel['special_instructions']}")
            print(f"   📅 {parcel['registration_timestamp'][:19].replace('T', ' ')}")
            print()

async def track_parcel():
    """Track a parcel by barcode or tracking number"""
    print("\n=== Parcel Tracking ===")
    
    identifier = input("Enter barcode or tracking number: ").strip()
    if not identifier:
        print("No identifier provided!")
        return
    
    async with ParcelTrackingDB() as db:
        # Try to find by barcode first
        parcel = await db.get_parcel_by_barcode(identifier)
        
        # If not found, try tracking number
        if not parcel:
            parcel = await db.get_parcel_by_tracking_number(identifier)
        
        if not parcel:
            print(f"❌ No parcel found with identifier: {identifier}")
            return
        
        # Show detailed tracking information
        print(f"\n📋 Parcel Details:")
        print(f"   📦 Barcode: {parcel['barcode']}")
        print(f"   🏷️  Tracking Number: {parcel['tracking_number']}")
        print(f"   📤 From: {parcel['sender_name']} ({parcel['sender_address']})")
        print(f"   📥 To: {parcel['recipient_name']} ({parcel['recipient_address']})")
        print(f"   🚚 Service: {parcel['service_type'].title()}")
        print(f"   📊 Current Status: {parcel['current_status'].title()}")
        print(f"   📍 Current Location: {parcel['current_location']}")
        print(f"   📅 Registered: {parcel['registration_timestamp'][:19].replace('T', ' ')}")
        print(f"   🎯 Estimated Delivery: {parcel['estimated_delivery'][:10]}")
        
        if parcel.get('weight'):
            print(f"   ⚖️  Weight: {parcel['weight']} kg")
        if parcel.get('dimensions'):
            print(f"   📏 Dimensions: {parcel['dimensions']}")
        if parcel.get('declared_value'):
            print(f"   💰 Declared Value: ${parcel['declared_value']:.2f}")
        if parcel.get('special_instructions'):
            print(f"   ⚠️  Special Instructions: {parcel['special_instructions']}")
        
        # Get tracking events
        tracking_events = await db.get_parcel_tracking_history(parcel['barcode'])
        
        if tracking_events:
            print(f"\n📈 Tracking History:")
            for i, event in enumerate(sorted(tracking_events, key=lambda x: x['timestamp']), 1):
                timestamp = event['timestamp'][:19].replace('T', ' ')
                print(f"   {i}. {timestamp} | {event['event_type'].title()}")
                print(f"      📍 {event['location']} | 👤 {event['scanned_by']}")
                print(f"      💬 {event['description']}")
                print()
        else:
            print("\n📈 No tracking history available yet.")

async def simulate_logistics_operations():
    """Simulate logistics operations (status updates)"""
    print("\n=== Simulating Logistics Operations ===")
    
    async with ParcelTrackingDB() as db:
        parcels = await db.get_all_parcels()
        
        if not parcels:
            print("📭 No parcels found to simulate operations on.")
            print("💡 Register some parcels first.")
            return
        
        # Simulate status updates for a few parcels
        import random
        operation_count = min(3, len(parcels))
        selected_parcels = random.sample(parcels, operation_count)
        
        status_progressions = [
            {'status': 'In Transit', 'location': 'Sorting_Facility_VIC', 'description': 'Parcel sorted and loaded onto transport'},
            {'status': 'At Depot', 'location': 'Distribution_Center_NSW', 'description': 'Arrived at distribution center'},
            {'status': 'Out for Delivery', 'location': 'Delivery_Vehicle_001', 'description': 'Out for delivery on vehicle'}
        ]
        
        for parcel in selected_parcels:
            # Pick a random status progression
            update = random.choice(status_progressions)
            
            print(f"\n🔄 Updating parcel {parcel['barcode']} to {update['status']}...")
            
            success = await db.update_parcel_status(
                barcode=parcel['barcode'],
                status=update['status'],
                location=update['location'],
                scanned_by="system_demo"
            )
            
            if success:
                print(f"✅ {update['description']}: {update['status']} at {update['location']}")
            else:
                print(f"❌ Failed to update parcel {parcel['barcode']}")
        
        print("\n🎉 Simulation completed!")

async def run_agent_workflow():
    """Run AI agent workflow for intelligent parcel processing"""
    print("\n=== AI Agent Workflow - Intelligent Parcel Processing ===")
    
    try:
        # Check if we have parcels to work with
        async with ParcelTrackingDB() as db:
            parcels = await db.get_all_parcels()
            
            if not parcels:
                print("📭 No parcels found to process with AI agents.")
                print("💡 Register some parcels first using option 1 or 2.")
                return
            
            # Check for pending approvals
            pending_approvals = await db.get_all_pending_approvals()
            
            print(f"🤖 Processing {len(parcels)} parcels with AI logistics agents...")
            if pending_approvals:
                print(f"📋 Found {len(pending_approvals)} pending approvals for agent review")
            
            print("\n🔄 Starting Real AI Agent Workflow...")
            print("   🎯 Launching W01_Sequential_Workflow_Human_Approval.py")
            
            # Actually run the AI workflow using wrapper script
            wrapper_script = "run_ai_workflow.py"
            
            print(f"   ▶️ Executing: python {wrapper_script}")
            print("   ⏳ Please wait while AI agents process your logistics data...\n")
            
            # Get the current directory (where main.py is located)
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Set up environment to include the parent directory in PYTHONPATH
            env = os.environ.copy()
            env['PYTHONPATH'] = current_dir + (';' + env.get('PYTHONPATH', '')) if env.get('PYTHONPATH') else current_dir
            
            # Run the actual AI workflow with proper working directory and environment
            result = subprocess.run([
                sys.executable, wrapper_script
            ], cwd=current_dir, env=env)
            
            if result.returncode == 0:
                print("\n✅ AI Agent Workflow completed successfully!")
                print("📊 Workflow Results:")
                print("-" * 60)
                print("🤖 All 9 logistics agents processed parcel data")
                print("📋 Parcel Intake → Sorting Facility → Delivery Coordination")
                print("📝 Supervisor approvals requested for critical actions")
                print("✨ Workflow execution completed with agent intelligence")
                    
            else:
                print(f"\n❌ AI Agent Workflow exited with code: {result.returncode}")
                print("💡 To run manually: python Scripts/W01_Sequential_Workflow_Human_Approval.py")
            
    except Exception as e:
        print(f"❌ Error running agent workflow: {str(e)}")
        print("💡 Alternative: Run manually with: python Scripts/W01_Sequential_Workflow_Human_Approval.py")

async def scan_parcel_at_location_demo():
    """Demonstrate location-aware parcel scanning"""
    print("\n=== Location-Aware Parcel Scanning ===")
    print("This simulates scanning a parcel as it moves through the logistics network")
    
    # Get parcel to scan
    barcode = input("Enter parcel barcode to scan: ").strip()
    if not barcode:
        print("❌ Barcode required")
        return
    
    # Show location options
    print("\n📍 Available Scan Locations:")
    locations = [
        "Store_Melbourne_CBD",
        "Depot_Melbourne_North", 
        "Sorting_Facility_VIC",
        "Distribution_Hub_Melbourne",
        "Delivery_Vehicle_001",
        "Customer_Address_123_Collins_St"
    ]
    
    for i, location in enumerate(locations, 1):
        print(f"  {i}. {location}")
    
    print("  7. Custom location")
    
    try:
        location_choice = int(input("\nSelect scan location (1-7): ").strip())
        if location_choice == 7:
            scan_location = input("Enter custom location: ").strip()
        elif 1 <= location_choice <= 6:
            scan_location = locations[location_choice - 1]
        else:
            print("❌ Invalid choice")
            return
    except ValueError:
        print("❌ Invalid choice")
        return
    
    # Scan type
    print("\n🔍 Scan Types:")
    scan_types = ["arrival", "departure", "processing", "loading"]
    for i, scan_type in enumerate(scan_types, 1):
        print(f"  {i}. {scan_type}")
    
    try:
        scan_type_choice = int(input("Select scan type (1-4) [1]: ").strip() or "1")
        if 1 <= scan_type_choice <= 4:
            scan_type = scan_types[scan_type_choice - 1]
        else:
            scan_type = "arrival"
    except ValueError:
        scan_type = "arrival"
    
    scanned_by = input("Scanned by (operator ID) [system]: ").strip() or "system"
    
    # Perform the scan
    async with ParcelTrackingDB() as db:
        result = await db.scan_parcel_at_location(
            barcode=barcode,
            scan_location=scan_location,
            scanned_by=scanned_by,
            scan_type=scan_type
        )
        
        if result["success"]:
            print(f"\n✅ Scan Successful!")
            print(f"📦 Barcode: {result['barcode']}")
            print(f"📍 Location: {result['previous_location']} → {result['current_location']}")
            print(f"📊 Status: {result['previous_status']} → {result['current_status']}")
            print(f"📝 Description: {result['description']}")
            print(f"👤 Scanned by: {result['scanned_by']}")
            print(f"🔍 Scan type: {result['scan_type']}")
            print(f"⏰ Timestamp: {result['timestamp']}")
        else:
            print(f"\n❌ Scan Failed: {result['error']}")

async def generate_test_data():
    """Generate random test parcels"""
    print("\n=== Generating Test Data ===")
    
    try:
        count = int(input("How many test parcels to generate? [5]: ").strip() or "5")
    except ValueError:
        count = 5
    
    async with ParcelTrackingDB() as db:
        parcels = await db.add_random_test_parcels(count)
        
        print(f"\n📊 Generated {len(parcels)} random test parcels:")
        for parcel in parcels:
            print(f"✅ {parcel['barcode']} → {parcel['tracking_number']}")
            print(f"   {parcel['sender_name']} → {parcel['recipient_name']} ({parcel['destination_postcode']})")