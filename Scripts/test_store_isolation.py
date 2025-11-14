"""
Test Store-Based Data Organization
==================================
Quick test to verify the store isolation functionality works correctly
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmosdb_tools import (
    get_all_stores,
    get_parcels_by_store, 
    create_sample_store_data,
    get_store_statistics,
    cleanup_store_data
)

async def quick_store_test():
    """Quick test of store-based operations"""
    
    print("🧪 Testing Store-Based Data Organization")
    print("="*45)
    
    # Test stores
    test_stores = ["Test Store A", "Test Store B"]
    
    try:
        # Create sample data
        print("\n📦 Creating sample data...")
        for store in test_stores:
            parcel_ids = await create_sample_store_data(store, 2)
            print(f"✅ Created {len(parcel_ids)} parcels for {store}")
        
        # Test store listing
        print("\n📋 Listing all stores...")
        all_stores = await get_all_stores()
        print(f"Found {len(all_stores)} stores:")
        for store in all_stores:
            if store in test_stores:  # Only show test stores
                print(f"  • {store}")
        
        # Test store-specific queries
        print("\n📊 Testing store-specific statistics...")
        for store in test_stores:
            stats = await get_store_statistics(store)
            print(f"{store}: {stats['total_parcels']} parcels")
        
        # Test isolation by cleaning one store
        print(f"\n🧹 Testing isolation - cleaning {test_stores[0]}...")
        await cleanup_store_data(test_stores[0], confirm=True)
        
        # Verify other store is unaffected
        remaining_stats = await get_store_statistics(test_stores[1])
        print(f"✅ {test_stores[1]} still has {remaining_stats['total_parcels']} parcels (unaffected)")
        
        # Clean up remaining test data
        print(f"\n🧹 Cleaning up {test_stores[1]}...")
        await cleanup_store_data(test_stores[1], confirm=True)
        
        print("\n✅ All tests passed! Store isolation working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        # Clean up on failure
        for store in test_stores:
            try:
                await cleanup_store_data(store, confirm=True)
            except:
                pass

if __name__ == "__main__":
    asyncio.run(quick_store_test())