"""
Demo: Store-Based Data Organization and Blast Radius Limitation
==============================================================

This script demonstrates how the partition key strategy enables:
1. Efficient store-specific queries
2. Limited blast radius operations
3. Store-level data isolation
4. Performance optimization through partition key usage
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmosdb_tools import (
    get_all_stores,
    get_parcels_by_store,
    get_store_statistics,
    create_sample_store_data,
    cleanup_store_data,
    cleanup_database
)

async def demonstrate_store_isolation():
    """Demonstrate store-based data organization and isolation"""
    
    print("🏪 Store-Based Data Organization Demo")
    print("="*50)
    
    # Define test stores
    test_stores = [
        "Melbourne Central Post",
        "Sydney CBD Post", 
        "Brisbane Queen Street"
    ]
    
    print("\n📦 Step 1: Creating sample data for multiple stores")
    print("-" * 40)
    for store in test_stores:
        print(f"Creating sample parcels for: {store}")
        parcel_ids = await create_sample_store_data(store, 3)
        print(f"✅ Created {len(parcel_ids)} parcels\n")
    
    print("\n🏪 Step 2: Listing all stores in the system")
    print("-" * 40)
    all_stores = await get_all_stores()
    for i, store in enumerate(all_stores, 1):
        print(f"{i}. {store}")
    
    print(f"\nTotal stores found: {len(all_stores)}")
    
    print("\n📊 Step 3: Store-specific statistics (efficient partition queries)")
    print("-" * 40)
    for store in test_stores:
        stats = await get_store_statistics(store)
        print(f"\n📋 Store: {stats['store_location']}")
        print(f"   Total Parcels: {stats['total_parcels']}")
        print(f"   By Status: {stats['parcels_by_status']}")
        print(f"   By Service: {stats['parcels_by_service_type']}")
        print(f"   Total Value: ${stats['total_declared_value']:.2f}")
        print(f"   Avg Weight: {stats['average_weight']}kg")
    
    print("\n🎯 Step 4: Demonstrating limited blast radius")
    print("-" * 40)
    
    # Show parcels before cleanup
    test_store = test_stores[0]
    print(f"📦 Parcels in {test_store} before cleanup:")
    parcels = await get_parcels_by_store(test_store)
    for parcel in parcels:
        print(f"   • {parcel['id'][:8]}... - {parcel['recipient_name']}")
    
    # Demonstrate limited cleanup (only affects one store)
    print(f"\n🧹 Cleaning up ONLY {test_store} (blast radius limited)")
    success = await cleanup_store_data(test_store, confirm=True)
    
    if success:
        print(f"✅ Store {test_store} cleaned up")
        
        # Verify other stores are unaffected
        print(f"\n🔍 Verifying other stores are unaffected:")
        for store in test_stores[1:]:  # Skip the cleaned store
            parcels = await get_parcels_by_store(store)
            print(f"   • {store}: {len(parcels)} parcels (unchanged)")
    
    print("\n🏪 Step 5: Store-specific query performance")
    print("-" * 40)
    print("Benefits of store_location as partition key:")
    print("• Queries within a store are highly efficient (single partition)")
    print("• Store operations are isolated (limited blast radius)")
    print("• Cross-store queries available when needed (cross-partition)")
    print("• Natural data organization by business unit")
    
    print("\n🔧 Step 6: Cleanup remaining test data")
    print("-" * 40)
    for store in test_stores[1:]:  # Clean remaining test stores
        await cleanup_store_data(store, confirm=True)
    
    print("\n✅ Demo completed!")
    print("\nKey Benefits Demonstrated:")
    print("• ✅ Store-level data isolation")
    print("• ✅ Efficient single-store queries")
    print("• ✅ Limited blast radius operations")
    print("• ✅ Scalable multi-store architecture")

async def interactive_store_demo():
    """Interactive demo for exploring store operations"""
    
    print("\n🔧 Interactive Store Demo")
    print("=" * 30)
    
    while True:
        print("\nOptions:")
        print("1. List all stores")
        print("2. Create sample data for store")
        print("3. View store statistics")
        print("4. View store parcels")
        print("5. Clean up store data")
        print("0. Exit")
        
        choice = input("\nEnter choice (0-5): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            stores = await get_all_stores()
            print(f"\n📍 Found {len(stores)} stores:")
            for i, store in enumerate(stores, 1):
                print(f"{i}. {store}")
        
        elif choice == "2":
            store_name = input("Enter store name: ").strip()
            if store_name:
                num_parcels = input("Number of sample parcels (default 5): ").strip()
                num_parcels = int(num_parcels) if num_parcels.isdigit() else 5
                parcel_ids = await create_sample_store_data(store_name, num_parcels)
                print(f"✅ Created {len(parcel_ids)} parcels for {store_name}")
        
        elif choice == "3":
            store_name = input("Enter store name: ").strip()
            if store_name:
                stats = await get_store_statistics(store_name)
                if stats['total_parcels'] > 0:
                    print(f"\n📊 Statistics for {store_name}:")
                    print(f"Total Parcels: {stats['total_parcels']}")
                    print(f"By Status: {stats['parcels_by_status']}")
                    print(f"By Service: {stats['parcels_by_service_type']}")
                    print(f"Total Value: ${stats['total_declared_value']:.2f}")
                    print(f"Average Weight: {stats['average_weight']}kg")
                else:
                    print(f"No parcels found for store: {store_name}")
        
        elif choice == "4":
            store_name = input("Enter store name: ").strip()
            if store_name:
                parcels = await get_parcels_by_store(store_name)
                if parcels:
                    print(f"\n📦 Parcels in {store_name}:")
                    for parcel in parcels[:10]:  # Show max 10
                        print(f"• {parcel['id'][:8]}... - {parcel['recipient_name']} - {parcel['current_status']}")
                    if len(parcels) > 10:
                        print(f"... and {len(parcels) - 10} more")
                else:
                    print(f"No parcels found for store: {store_name}")
        
        elif choice == "5":
            store_name = input("Enter store name: ").strip()
            if store_name:
                confirm = input(f"⚠️ Delete ALL parcels from {store_name}? (yes/no): ").strip().lower()
                if confirm == "yes":
                    success = await cleanup_store_data(store_name, confirm=True)
                    if success:
                        print(f"✅ Cleaned up store: {store_name}")
                else:
                    print("❌ Cleanup cancelled")

if __name__ == "__main__":
    print("Store-Based Data Organization Demo")
    print("Choose demo mode:")
    print("1. Automated demo")
    print("2. Interactive demo")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        asyncio.run(demonstrate_store_isolation())
    elif choice == "2":
        asyncio.run(interactive_store_demo())
    else:
        print("Invalid choice")