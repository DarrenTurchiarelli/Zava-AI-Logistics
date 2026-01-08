"""
Script to delete and recreate driver001's manifest with accurate route data
This fixes the issue where safest route showed placeholder estimates instead of real Azure Maps data
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parcel_tracking_db import ParcelTrackingDB


async def refresh_driver001_manifest():
    """Delete old manifest and create fresh one with accurate routes"""
    
    async with ParcelTrackingDB() as db:
        print("\n" + "="*60)
        print("🔄 REFRESHING DRIVER001 MANIFEST")
        print("="*60 + "\n")
        
        # Step 1: Get current manifest
        print("📋 Step 1: Finding driver001's current manifest...")
        container = db.database.get_container_client("driver_manifests")
        
        query = "SELECT * FROM c WHERE c.driver_id = @driver_id AND c.status = 'active'"
        parameters = [{"name": "@driver_id", "value": "driver-001"}]
        
        old_manifest = None
        async for manifest in container.query_items(query=query, parameters=parameters):
            old_manifest = manifest
            break
        
        if old_manifest:
            print(f"   ✓ Found manifest: {old_manifest['id']}")
            print(f"   - Created: {old_manifest.get('created_date', 'N/A')}")
            print(f"   - Parcels: {len(old_manifest.get('items', []))}")
            print(f"   - Current route type: {old_manifest.get('selected_route_type', 'N/A')}")
            
            # Check if it has the old placeholder data
            all_routes = old_manifest.get('all_routes', {})
            if 'safest' in all_routes:
                safest = all_routes['safest']
                print(f"   - Safest route: {safest.get('total_duration_minutes')} min, {safest.get('total_distance_km')} km")
                
                # Check if it's placeholder data (suspiciously round numbers)
                if safest.get('total_distance_km', 0) < 10 and safest.get('total_duration_minutes', 0) < 60:
                    print(f"   ⚠️  WARNING: This looks like placeholder data!")
            
            # Step 2: Delete old manifest
            print("\n📋 Step 2: Deleting old manifest...")
            try:
                await container.delete_item(item=old_manifest['id'], partition_key=old_manifest['driver_id'])
                print("   ✓ Old manifest deleted successfully")
            except Exception as e:
                print(f"   ❌ Error deleting manifest: {e}")
                return False
        else:
            print("   ℹ️  No active manifest found for driver001")
        
        # Step 3: Get parcels for driver001
        print("\n📋 Step 3: Finding parcels assigned to driver001...")
        parcels_container = db.database.get_container_client("parcels")
        
        query = """
        SELECT * FROM c 
        WHERE c.current_status = 'out_for_delivery' 
        AND CONTAINS(LOWER(c.current_location), 'driver-001')
        """
        
        parcels = []
        async for parcel in parcels_container.query_items(query=query):
            parcels.append(parcel)
        
        print(f"   ✓ Found {len(parcels)} parcels assigned to driver001")
        
        if len(parcels) == 0:
            print("\n   ⚠️  No parcels found! Please assign some parcels to driver001 first.")
            print("   Suggestion: Run the manifest generator or assign parcels manually")
            return False
        
        # Step 4: Create new manifest with accurate route calculation
        print("\n📋 Step 4: Creating new manifest with accurate Azure Maps routes...")
        print("   This will calculate ALL THREE route types (fastest, shortest, safest)")
        print("   using real Azure Maps API data...\n")
        
        # Import required modules
        from datetime import datetime, timezone
        from config.depots import get_depot_manager
        from services.maps import BingMapsRouter
        
        # Get unique addresses
        addresses = list(set([p['recipient_address'] for p in parcels]))
        print(f"   → {len(addresses)} unique delivery addresses")
        
        # Get depot location
        depot_mgr = get_depot_manager()
        start_location = depot_mgr.get_closest_depot_to_address(addresses[0])
        print(f"   → Starting from: {start_location}")
        
        # Calculate routes
        router = BingMapsRouter()
        print(f"\n   🗺️  Calling Azure Maps API to calculate routes...")
        all_routes = router.optimize_all_route_types(addresses, start_location)
        
        if not all_routes or 'safest' not in all_routes:
            print(f"   ❌ Failed to calculate routes with Azure Maps")
            return False
        
        print(f"\n   ✓ Routes calculated successfully:")
        print(f"      Fastest:  {all_routes['fastest']['total_duration_minutes']} min, {all_routes['fastest']['total_distance_km']} km")
        print(f"      Shortest: {all_routes['shortest']['total_duration_minutes']} min, {all_routes['shortest']['total_distance_km']} km")
        print(f"      Safest:   {all_routes['safest']['total_duration_minutes']} min, {all_routes['safest']['total_distance_km']} km")
        
        # Create new manifest
        import uuid
        new_manifest_id = str(uuid.uuid4())
        
        manifest_items = []
        for parcel in parcels:
            manifest_items.append({
                'barcode': parcel['barcode'],
                'tracking_number': parcel['tracking_number'],
                'recipient_name': parcel['recipient_name'],
                'recipient_address': parcel['recipient_address'],
                'postcode': parcel['destination_postcode'],
                'service_type': parcel.get('service_type', 'standard'),
                'weight': parcel.get('weight', 0),
                'status': 'pending'
            })
        
        safest_route = all_routes['safest']
        
        new_manifest = {
            'id': new_manifest_id,
            'driver_id': 'driver-001',
            'driver_name': 'Driver 001',
            'created_date': datetime.now(timezone.utc).isoformat(),
            'status': 'active',
            'items': manifest_items,
            'total_items': len(manifest_items),
            'completed_items': 0,
            'route_optimized': True,
            'optimized_route': safest_route['waypoints'],
            'estimated_duration_minutes': safest_route['total_duration_minutes'],
            'estimated_distance_km': safest_route['total_distance_km'],
            'selected_route_type': 'safest',
            'multi_route_enabled': True,
            'all_routes': all_routes,
            'traffic_considered': safest_route.get('traffic_considered', False)
        }
        
        print(f"\n   📝 Saving new manifest to Cosmos DB...")
        await container.create_item(body=new_manifest)
        print(f"   ✓ New manifest created: {new_manifest_id}")
        
        print("\n" + "="*60)
        print("✅ MANIFEST REFRESH COMPLETE!")
        print("="*60)
        print(f"\n📊 Summary:")
        print(f"   - Manifest ID: {new_manifest_id}")
        print(f"   - Driver: driver-001")
        print(f"   - Parcels: {len(manifest_items)}")
        print(f"   - Routes calculated: 3 (fastest, shortest, safest)")
        print(f"   - Selected route: Safest ({safest_route['total_duration_minutes']} min, {safest_route['total_distance_km']} km)")
        print(f"\n🌐 View manifest at: http://127.0.0.1:5000/driver/manifest")
        print("   (Login as driver001 / driver001)\n")
        
        return True


if __name__ == "__main__":
    result = asyncio.run(refresh_driver001_manifest())
    sys.exit(0 if result else 1)
