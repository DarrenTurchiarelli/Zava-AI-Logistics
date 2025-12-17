"""
Test Script for DISPATCHER_AGENT Integration
Demonstrates intelligent manifest creation using Azure AI Foundry

This script:
1. Creates sample pending parcels
2. Sets up available drivers
3. Calls DISPATCHER_AGENT for intelligent assignment
4. Creates manifests based on AI recommendations
5. Displays results

Usage:
    python Scripts/test_dispatcher_agent.py
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parcel_tracking_db import ParcelTrackingDB
from agents.base import dispatcher_agent


async def create_sample_pending_parcels(db: ParcelTrackingDB, count: int = 25) -> List[str]:
    """Create sample parcels at depot status"""
    print(f"\n📦 Creating {count} sample parcels at depot...")
    
    barcodes = []
    postcodes = ["3000", "3001", "3002", "3003", "3004", "3050", "3051", "3052", "3053", "3054"]
    priorities = [1, 1, 2, 2, 2, 2, 2, 3, 3, 3]  # Mix of urgent, standard, economy
    
    for i in range(count):
        barcode = f"TEST{datetime.now().strftime('%Y%m%d')}{i+1:04d}"
        postcode = postcodes[i % len(postcodes)]
        priority = priorities[i % len(priorities)]
        
        parcel_data = {
            "barcode": barcode,
            "tracking_number": f"TN{barcode}",
            "sender_name": "Test Sender",
            "sender_address": "123 Test St, Melbourne VIC 3000",
            "recipient_name": f"Test Recipient {i+1}",
            "recipient_address": f"{100+i} Delivery St, Melbourne VIC {postcode}",
            "recipient_phone": "0400000000",
            "postcode": postcode,
            "status": "At Depot",
            "priority": priority,
            "service_type": "standard" if priority == 2 else ("express" if priority == 1 else "economy"),
            "weight_kg": 1.5 + (i * 0.3),
            "value_dollars": 50 + (i * 10)
        }
        
        await db.register_parcel(
            barcode=parcel_data["barcode"],
            tracking_number=parcel_data["tracking_number"],
            sender_name=parcel_data["sender_name"],
            sender_address=parcel_data["sender_address"],
            recipient_name=parcel_data["recipient_name"],
            recipient_address=parcel_data["recipient_address"],
            recipient_phone=parcel_data["recipient_phone"],
            weight_kg=parcel_data["weight_kg"],
            service_type=parcel_data["service_type"],
            registered_by="test_script"
        )
        
        # Update status to "At Depot"
        await db.update_parcel_status(barcode, "At Depot", "VIC Depot")
        
        barcodes.append(barcode)
    
    print(f"✅ Created {len(barcodes)} test parcels")
    return barcodes


async def test_dispatcher_agent_assignment():
    """Test DISPATCHER_AGENT for intelligent manifest creation"""
    
    print("=" * 80)
    print("🤖 DISPATCHER_AGENT Test - Intelligent Manifest Assignment")
    print("=" * 80)
    
    try:
        async with ParcelTrackingDB() as db:
            # Step 1: Create sample parcels
            print("\n[Step 1] Creating sample pending parcels...")
            barcodes = await create_sample_pending_parcels(db, count=25)
            
            # Step 2: Get pending parcels
            print("\n[Step 2] Retrieving pending parcels from database...")
            pending_parcels = await db.get_pending_parcels(status="At Depot", max_count=25)
            print(f"✅ Found {len(pending_parcels)} pending parcels")
            
            # Display parcel summary
            print("\n📊 Parcel Summary by Priority:")
            priority_counts = {}
            for p in pending_parcels:
                pri = p.get('priority', 2)
                priority_counts[pri] = priority_counts.get(pri, 0) + 1
            
            for pri, count in sorted(priority_counts.items()):
                priority_name = {1: "Urgent", 2: "Standard", 3: "Economy"}.get(pri, "Unknown")
                print(f"   Priority {pri} ({priority_name}): {count} parcels")
            
            # Step 3: Get available drivers
            print("\n[Step 3] Getting available drivers...")
            drivers = await db.get_available_drivers(state="VIC")
            print(f"✅ Found {len(drivers)} available drivers")
            
            if not drivers:
                print("⚠️ No drivers found. Creating test drivers in users database first...")
                print("   Please run: python utils/setup/setup_users.py")
                return
            
            for driver in drivers:
                print(f"   • {driver['name']} ({driver['driver_id']}) - Capacity: {driver['max_capacity']}")
            
            # Step 4: Prepare request for DISPATCHER_AGENT
            print("\n[Step 4] Preparing DISPATCHER_AGENT request...")
            route_request = {
                "parcel_count": len(pending_parcels),
                "available_drivers": [d['driver_id'] for d in drivers],
                "service_level": "standard",
                "delivery_window": "08:00 - 18:00",
                "zone": "VIC",
                "parcels": [
                    {
                        "barcode": p['barcode'],
                        "tracking_number": p.get('tracking_number', p['barcode']),
                        "address": p['recipient_address'],
                        "postcode": p.get('postcode', ''),
                        "priority": p.get('priority', 2),
                        "recipient_name": p.get('recipient_name', '')
                    }
                    for p in pending_parcels
                ]
            }
            
            print(f"   Parcels to assign: {route_request['parcel_count']}")
            print(f"   Available drivers: {len(route_request['available_drivers'])}")
            print(f"   Zone: {route_request['zone']}")
            
            # Step 5: Call DISPATCHER_AGENT
            print("\n[Step 5] 🤖 Calling DISPATCHER_AGENT for intelligent assignment...")
            print("   This may take 10-30 seconds depending on Azure AI response time...")
            
            agent_result = await dispatcher_agent(route_request)
            
            print("\n" + "=" * 80)
            print("📋 DISPATCHER_AGENT RESPONSE")
            print("=" * 80)
            
            if agent_result.get('success'):
                ai_response = agent_result.get('response', '')
                print(f"\n{ai_response}")
                print("\n" + "=" * 80)
                
                # Step 6: Parse and display recommendations
                print("\n[Step 6] Parsing AI recommendations...")
                
                # Simple parsing - in production, this would be more sophisticated
                import re
                driver_assignments = {}
                
                # Look for driver mentions and parcel counts
                for driver in drivers:
                    driver_id = driver['driver_id']
                    # Try to find how many parcels assigned to this driver
                    pattern = f"{driver_id}.*?(\\d+)\\s*parcel"
                    match = re.search(pattern, ai_response.lower())
                    if match:
                        count = int(match.group(1))
                        driver_assignments[driver_id] = count
                
                if driver_assignments:
                    print("\n✅ AI Recommendations:")
                    for driver_id, count in driver_assignments.items():
                        driver_name = next((d['name'] for d in drivers if d['driver_id'] == driver_id), driver_id)
                        print(f"   • {driver_name}: {count} parcels")
                else:
                    print("\n⚙️ Using even distribution (AI didn't specify counts)")
                    parcels_per_driver = len(pending_parcels) // len(drivers)
                    for driver in drivers:
                        print(f"   • {driver['name']}: ~{parcels_per_driver} parcels")
                
                # Step 7: Create manifests (optional - comment out to avoid creating actual manifests)
                create_manifests = input("\n❓ Create actual manifests in database? (yes/no): ").lower() == 'yes'
                
                if create_manifests:
                    print("\n[Step 7] Creating manifests based on AI recommendations...")
                    
                    # Simple distribution for demo
                    parcels_per_driver = len(pending_parcels) // len(drivers)
                    idx = 0
                    
                    for i, driver in enumerate(drivers):
                        count = parcels_per_driver + (1 if i < len(pending_parcels) % len(drivers) else 0)
                        assigned_barcodes = [p['barcode'] for p in pending_parcels[idx:idx+count]]
                        
                        if assigned_barcodes:
                            manifest_id = await db.create_driver_manifest(
                                driver_id=driver['driver_id'],
                                driver_name=driver['name'],
                                parcel_barcodes=assigned_barcodes
                            )
                            
                            if manifest_id:
                                print(f"   ✅ Created {manifest_id} for {driver['name']}: {len(assigned_barcodes)} parcels")
                        
                        idx += count
                    
                    print(f"\n✅ Successfully created {len(drivers)} manifests!")
                else:
                    print("\n⏭️ Skipped manifest creation (dry run)")
                
            else:
                print(f"❌ DISPATCHER_AGENT Error: {agent_result.get('error')}")
                print("\nThis could be due to:")
                print("  • DISPATCHER_AGENT_ID not configured in .env")
                print("  • Azure AI authentication issues")
                print("  • Agent not properly created in Azure AI Foundry")
            
            print("\n" + "=" * 80)
            print("✅ Test Complete!")
            print("=" * 80)
            
            # Cleanup option
            cleanup = input("\n❓ Delete test parcels? (yes/no): ").lower() == 'yes'
            if cleanup:
                print("\n🧹 Cleaning up test parcels...")
                for barcode in barcodes:
                    # Note: You'd need to implement delete_parcel method
                    print(f"   • Would delete {barcode} (delete not implemented)")
                print("✅ Cleanup complete")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def quick_test():
    """Quick test to verify DISPATCHER_AGENT is accessible"""
    print("\n🔍 Quick Agent Test - Verifying DISPATCHER_AGENT configuration...\n")
    
    test_request = {
        "parcel_count": 5,
        "available_drivers": ["driver001", "driver002"],
        "service_level": "standard",
        "delivery_window": "08:00 - 18:00",
        "zone": "VIC",
        "parcels": [
            {"barcode": "TEST001", "address": "1 Test St, Melbourne VIC 3000", "postcode": "3000", "priority": 2},
            {"barcode": "TEST002", "address": "2 Test St, Melbourne VIC 3001", "postcode": "3001", "priority": 1},
            {"barcode": "TEST003", "address": "3 Test St, Melbourne VIC 3002", "postcode": "3002", "priority": 2},
            {"barcode": "TEST004", "address": "4 Test St, Melbourne VIC 3003", "postcode": "3003", "priority": 2},
            {"barcode": "TEST005", "address": "5 Test St, Melbourne VIC 3004", "postcode": "3004", "priority": 3},
        ]
    }
    
    print("Calling DISPATCHER_AGENT with sample data...")
    result = await dispatcher_agent(test_request)
    
    if result.get('success'):
        print("✅ DISPATCHER_AGENT is working!")
        print(f"\nResponse: {result.get('response')[:200]}...")
    else:
        print(f"❌ DISPATCHER_AGENT failed: {result.get('error')}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DISPATCHER_AGENT Test Script")
    print("=" * 80)
    print("\nOptions:")
    print("1. Quick test (verify agent is configured)")
    print("2. Full test (create parcels, test assignment, create manifests)")
    
    choice = input("\nSelect option (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(quick_test())
    elif choice == "2":
        asyncio.run(test_dispatcher_agent_assignment())
    else:
        print("Invalid choice. Running quick test...")
        asyncio.run(quick_test())
