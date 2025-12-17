"""
Test script for Parcel Intake Agent - Enhanced Implementation
Tests the fully integrated parcel validation with AI recommendations
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.base import parcel_intake_agent


async def test_standard_parcel():
    """Test validation of a standard parcel"""
    print("\n" + "="*70)
    print("TEST 1: Standard Parcel Validation")
    print("="*70)
    
    parcel_data = {
        'tracking_number': 'DTTEST001',
        'sender_name': 'John Smith',
        'sender_address': '123 Main Street, Melbourne VIC 3000',
        'recipient_name': 'Jane Doe',
        'recipient_address': '456 High Street, Sydney NSW 2000',
        'destination_postcode': '2000',
        'destination_state': 'NSW',
        'service_type': 'standard',
        'weight_kg': 2.5,
        'dimensions': '30x20x15cm',
        'declared_value': 50.0,
        'special_instructions': 'None'
    }
    
    print(f"\n📦 Testing parcel: {parcel_data['tracking_number']}")
    print(f"   From: {parcel_data['sender_name']} ({parcel_data['sender_address'][:30]}...)")
    print(f"   To: {parcel_data['recipient_name']} ({parcel_data['destination_postcode']})")
    print(f"   Service: {parcel_data['service_type'].title()}, Weight: {parcel_data['weight_kg']}kg")
    
    result = await parcel_intake_agent(parcel_data)
    
    if result.get('success'):
        print("\n✅ Validation completed successfully!")
        print(f"\n🤖 AI Feedback:\n{result.get('content', 'No feedback available')}")
    else:
        print(f"\n❌ Validation failed: {result.get('error', 'Unknown error')}")


async def test_high_value_parcel():
    """Test validation of a high-value parcel (should recommend upgraded service)"""
    print("\n" + "="*70)
    print("TEST 2: High-Value Parcel (Service Recommendation Test)")
    print("="*70)
    
    parcel_data = {
        'tracking_number': 'DTTEST002',
        'sender_name': 'Tech Store Melbourne',
        'sender_address': '789 Tech Boulevard, Melbourne VIC 3000',
        'recipient_name': 'Sarah Johnson',
        'recipient_address': '12 Beach Road, Brisbane QLD 4000',
        'destination_postcode': '4000',
        'destination_state': 'QLD',
        'service_type': 'standard',  # Should recommend Express/Overnight
        'weight_kg': 1.2,
        'dimensions': '25x20x10cm',
        'declared_value': 2500.0,  # High value!
        'special_instructions': 'Fragile - Electronics'
    }
    
    print(f"\n📦 Testing parcel: {parcel_data['tracking_number']}")
    print(f"   💰 HIGH VALUE: ${parcel_data['declared_value']}")
    print(f"   Current Service: {parcel_data['service_type'].title()}")
    print(f"   Expected: AI should recommend Express/Overnight service")
    
    result = await parcel_intake_agent(parcel_data)
    
    if result.get('success'):
        print("\n✅ Validation completed!")
        content = result.get('content', '').lower()
        if 'express' in content or 'overnight' in content or 'upgrade' in content:
            print("   ✅ AI correctly recommended service upgrade!")
        print(f"\n🤖 AI Feedback:\n{result.get('content', 'No feedback available')}")
    else:
        print(f"\n❌ Validation failed: {result.get('error', 'Unknown error')}")


async def test_incomplete_address():
    """Test validation with incomplete address (should flag issues)"""
    print("\n" + "="*70)
    print("TEST 3: Incomplete Address (Address Validation Test)")
    print("="*70)
    
    parcel_data = {
        'tracking_number': 'DTTEST003',
        'sender_name': 'Bob Builder',
        'sender_address': 'Somewhere in Sydney',  # Incomplete!
        'recipient_name': 'Alice Wonder',
        'recipient_address': 'Main St',  # Very incomplete!
        'destination_postcode': '3000',
        'destination_state': 'VIC',
        'service_type': 'standard',
        'weight_kg': 5.0,
        'dimensions': '40x30x20cm',
        'declared_value': 100.0,
        'special_instructions': 'None'
    }
    
    print(f"\n📦 Testing parcel: {parcel_data['tracking_number']}")
    print(f"   ⚠️ INCOMPLETE ADDRESSES:")
    print(f"   Sender: '{parcel_data['sender_address']}'")
    print(f"   Recipient: '{parcel_data['recipient_address']}'")
    print(f"   Expected: AI should flag incomplete addresses")
    
    result = await parcel_intake_agent(parcel_data)
    
    if result.get('success'):
        print("\n✅ Validation completed!")
        content = result.get('content', '').lower()
        if 'address' in content and ('incomplete' in content or 'missing' in content or 'invalid' in content):
            print("   ✅ AI correctly identified address issues!")
        print(f"\n🤖 AI Feedback:\n{result.get('content', 'No feedback available')}")
    else:
        print(f"\n❌ Validation failed: {result.get('error', 'Unknown error')}")


async def test_oversized_parcel():
    """Test validation of oversized parcel (should suggest complications)"""
    print("\n" + "="*70)
    print("TEST 4: Oversized Parcel (Complication Detection Test)")
    print("="*70)
    
    parcel_data = {
        'tracking_number': 'DTTEST004',
        'sender_name': 'Furniture Store',
        'sender_address': '100 Warehouse Road, Perth WA 6000',
        'recipient_name': 'David Wilson',
        'recipient_address': '25 Remote Lane, Darwin NT 0800',
        'destination_postcode': '0800',
        'destination_state': 'NT',
        'service_type': 'standard',  # May need freight upgrade
        'weight_kg': 25.0,  # Heavy!
        'dimensions': '120x80x60cm',  # Large!
        'declared_value': 800.0,
        'special_instructions': 'Large furniture item'
    }
    
    print(f"\n📦 Testing parcel: {parcel_data['tracking_number']}")
    print(f"   📏 OVERSIZED: {parcel_data['dimensions']}, {parcel_data['weight_kg']}kg")
    print(f"   🌏 Remote destination: {parcel_data['destination_state']}")
    print(f"   Expected: AI should flag size/weight and remote delivery")
    
    result = await parcel_intake_agent(parcel_data)
    
    if result.get('success'):
        print("\n✅ Validation completed!")
        content = result.get('content', '').lower()
        if 'freight' in content or 'oversized' in content or 'remote' in content or 'special' in content:
            print("   ✅ AI correctly identified complications!")
        print(f"\n🤖 AI Feedback:\n{result.get('content', 'No feedback available')}")
    else:
        print(f"\n❌ Validation failed: {result.get('error', 'Unknown error')}")


async def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*70)
    print("🧪 PARCEL INTAKE AGENT - ENHANCED VALIDATION TESTS")
    print("="*70)
    print("\nTesting AI-powered parcel validation with:")
    print("  ✓ Service type recommendations")
    print("  ✓ Address validation")
    print("  ✓ Delivery complication detection")
    print("  ✓ Data quality verification")
    
    try:
        await test_standard_parcel()
        await test_high_value_parcel()
        await test_incomplete_address()
        await test_oversized_parcel()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED")
        print("="*70)
        print("\nThe Parcel Intake Agent is now fully integrated!")
        print("Test parcels by registering at: http://127.0.0.1:5000/parcels/register")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Starting Parcel Intake Agent validation tests...")
    asyncio.run(run_all_tests())
