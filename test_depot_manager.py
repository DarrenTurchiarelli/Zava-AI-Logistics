#!/usr/bin/env python3
"""
Test Depot Manager Functionality

Demonstrates intelligent depot selection for multi-state deliveries.
Run with: python test_depot_manager.py
"""

import os
from dotenv import load_dotenv
from depot_manager import DepotManager, get_depot_for_addresses

load_dotenv()


def test_state_extraction():
    """Test state extraction from various address formats"""
    print("=" * 70)
    print("Test 1: State Extraction from Addresses")
    print("=" * 70)
    print()
    
    manager = DepotManager()
    
    test_cases = [
        ("123 George Street, Sydney NSW 2000", "NSW"),
        ("456 Collins Street, Melbourne VIC 3000", "VIC"),
        ("789 Queen Street, Brisbane QLD 4000", "QLD"),
        ("321 King William Street, Adelaide SA 5000", "SA"),
        ("654 Wellington Street, Perth WA 6000", "WA"),
        ("147 Elizabeth Street, Hobart TAS 7000", "TAS"),
        ("258 Northbourne Avenue, Canberra ACT 2600", "ACT"),
        ("369 Mitchell Street, Darwin NT 0800", "NT"),
        ("Invalid address without state code", None),
    ]
    
    passed = 0
    failed = 0
    
    for address, expected_state in test_cases:
        detected_state = manager.extract_state_from_address(address)
        status = "✅" if detected_state == expected_state else "❌"
        
        print(f"{status} Address: {address}")
        print(f"   Expected: {expected_state}")
        print(f"   Detected: {detected_state}")
        
        if detected_state == expected_state:
            passed += 1
        else:
            failed += 1
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    print()


def test_depot_lookup():
    """Test depot lookup by state"""
    print("=" * 70)
    print("Test 2: Depot Lookup by State")
    print("=" * 70)
    print()
    
    manager = DepotManager()
    
    print("Configured Depots:")
    for state, address in manager.list_depots().items():
        print(f"   {state}: {address}")
    print()
    
    # Test direct state lookup
    test_states = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'ACT', 'NT']
    
    for state in test_states:
        depot = manager.get_depot(state)
        status = "✅" if depot else "❌"
        print(f"{status} {state}: {depot}")
    print()


def test_single_address_depot_selection():
    """Test depot selection for individual addresses"""
    print("=" * 70)
    print("Test 3: Single Address Depot Selection")
    print("=" * 70)
    print()
    
    manager = DepotManager()
    
    test_addresses = [
        "1 Macquarie Street, Sydney NSW 2000",
        "100 Collins Street, Melbourne VIC 3000",
        "200 Queen Street, Brisbane QLD 4000",
        "50 North Terrace, Adelaide SA 5000",
    ]
    
    for address in test_addresses:
        state = manager.extract_state_from_address(address)
        depot = manager.get_depot_for_address(address)
        print(f"📍 Address: {address}")
        print(f"   → State: {state}")
        print(f"   → Selected Depot: {depot}")
        print()


def test_multi_address_depot_selection():
    """Test optimal depot selection for multiple addresses"""
    print("=" * 70)
    print("Test 4: Multi-Address Depot Selection (Smart Routing)")
    print("=" * 70)
    print()
    
    manager = DepotManager()
    
    # Scenario 1: All NSW addresses
    print("📦 Scenario 1: All deliveries in NSW")
    nsw_addresses = [
        "1 Macquarie Street, Sydney NSW 2000",
        "88 Cumberland Street, The Rocks NSW 2000",
        "483 George Street, Sydney NSW 2000",
        "201 Kent Street, Sydney NSW 2000",
    ]
    depot = manager.get_depot_for_addresses(nsw_addresses)
    print(f"   Addresses: {len(nsw_addresses)} locations in NSW")
    print(f"   ✅ Selected Depot: {depot}")
    print()
    
    # Scenario 2: All VIC addresses
    print("📦 Scenario 2: All deliveries in VIC")
    vic_addresses = [
        "100 Collins Street, Melbourne VIC 3000",
        "250 Flinders Street, Melbourne VIC 3000",
        "50 Bourke Street, Melbourne VIC 3000",
    ]
    depot = manager.get_depot_for_addresses(vic_addresses)
    print(f"   Addresses: {len(vic_addresses)} locations in VIC")
    print(f"   ✅ Selected Depot: {depot}")
    print()
    
    # Scenario 3: Mixed states (majority NSW)
    print("📦 Scenario 3: Mixed states (NSW majority)")
    mixed_addresses = [
        "1 Macquarie Street, Sydney NSW 2000",
        "88 Cumberland Street, The Rocks NSW 2000",
        "483 George Street, Sydney NSW 2000",
        "100 Collins Street, Melbourne VIC 3000",  # Only 1 VIC
    ]
    depot = manager.get_depot_for_addresses(mixed_addresses)
    state_counts = {}
    for addr in mixed_addresses:
        state = manager.extract_state_from_address(addr)
        state_counts[state] = state_counts.get(state, 0) + 1
    print(f"   Distribution: {state_counts}")
    print(f"   ✅ Selected Depot: {depot}")
    print()
    
    # Scenario 4: Multiple states
    print("📦 Scenario 4: Multi-state deliveries")
    multi_state_addresses = [
        "1 Macquarie Street, Sydney NSW 2000",
        "100 Collins Street, Melbourne VIC 3000",
        "200 Queen Street, Brisbane QLD 4000",
        "250 Flinders Street, Melbourne VIC 3000",
        "300 George Street, Sydney NSW 2000",
    ]
    depot = manager.get_depot_for_addresses(multi_state_addresses)
    state_counts = {}
    for addr in multi_state_addresses:
        state = manager.extract_state_from_address(addr)
        state_counts[state] = state_counts.get(state, 0) + 1
    print(f"   Distribution: {state_counts}")
    print(f"   ✅ Selected Depot: {depot}")
    print()


def test_route_optimization_scenario():
    """Simulate real-world route optimization scenario"""
    print("=" * 70)
    print("Test 5: Real-World Route Optimization Scenario")
    print("=" * 70)
    print()
    
    manager = DepotManager()
    
    # Simulate a driver manifest for Melbourne
    print("🚚 Driver Manifest: Melbourne Route")
    melbourne_deliveries = [
        "100 Collins Street, Melbourne VIC 3000",
        "250 Flinders Street, Melbourne VIC 3000",
        "50 Bourke Street, Melbourne VIC 3000",
        "150 Lonsdale Street, Melbourne VIC 3000",
        "300 Queen Street, Melbourne VIC 3000",
        "75 Spencer Street, Melbourne VIC 3004",
        "200 Victoria Street, Carlton VIC 3053",
        "88 Acland Street, St Kilda VIC 3182",
    ]
    
    start_depot = manager.get_depot_for_addresses(melbourne_deliveries)
    print(f"   Starting Depot: {start_depot}")
    print(f"   Delivery Stops: {len(melbourne_deliveries)}")
    print()
    
    print("   Delivery Route:")
    print(f"   0. 🏭 START: {start_depot}")
    for i, addr in enumerate(melbourne_deliveries, 1):
        print(f"   {i}. 📦 {addr}")
    print(f"   {len(melbourne_deliveries) + 1}. 🏭 END: {start_depot}")
    print()
    
    # Simulate a driver manifest for Sydney
    print("🚚 Driver Manifest: Sydney Route")
    sydney_deliveries = [
        "1 Macquarie Street, Sydney NSW 2000",
        "88 Cumberland Street, The Rocks NSW 2000",
        "483 George Street, Sydney NSW 2000",
        "201 Kent Street, Sydney NSW 2000",
        "100 Market Street, Sydney NSW 2000",
    ]
    
    start_depot = manager.get_depot_for_addresses(sydney_deliveries)
    print(f"   Starting Depot: {start_depot}")
    print(f"   Delivery Stops: {len(sydney_deliveries)}")
    print()
    
    print("   Delivery Route:")
    print(f"   0. 🏭 START: {start_depot}")
    for i, addr in enumerate(sydney_deliveries, 1):
        print(f"   {i}. 📦 {addr}")
    print(f"   {len(sydney_deliveries) + 1}. 🏭 END: {start_depot}")
    print()


def test_convenience_function():
    """Test the convenience function"""
    print("=" * 70)
    print("Test 6: Convenience Function")
    print("=" * 70)
    print()
    
    addresses = [
        "200 Queen Street, Brisbane QLD 4000",
        "250 Adelaide Street, Brisbane QLD 4000",
        "300 Edward Street, Brisbane QLD 4000",
    ]
    
    # Using convenience function (no need to instantiate manager)
    depot = get_depot_for_addresses(addresses)
    
    print(f"📦 Quick Lookup for {len(addresses)} Brisbane addresses:")
    print(f"   ✅ Depot: {depot}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" DEPOT MANAGER COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print()
    
    # Check if depots are configured
    manager = DepotManager()
    if not manager.list_depots():
        print("⚠️  WARNING: No depots configured in .env file!")
        print("   Add DEPOT_NSW, DEPOT_VIC, etc. to your .env file")
        print()
    
    # Run all tests
    test_state_extraction()
    test_depot_lookup()
    test_single_address_depot_selection()
    test_multi_address_depot_selection()
    test_route_optimization_scenario()
    test_convenience_function()
    
    print("=" * 70)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 70)
    print()
    print("💡 Key Features Demonstrated:")
    print("   • Automatic state detection from addresses")
    print("   • State-specific depot configuration")
    print("   • Single-address depot selection")
    print("   • Multi-address intelligent depot selection")
    print("   • Real-world route optimization scenarios")
    print("   • Convenience functions for quick lookups")
    print()
    print("🚀 The Depot Manager will automatically select the optimal depot")
    print("   based on delivery addresses when generating driver manifests!")
    print()
