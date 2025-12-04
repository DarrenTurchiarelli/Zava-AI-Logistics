"""
Test script to validate Azure Maps subscription key
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_azure_maps_key():
    """Test Azure Maps API with a simple geocoding request"""
    
    subscription_key = os.getenv('AZURE_MAPS_SUBSCRIPTION_KEY')
    
    if not subscription_key:
        print("❌ AZURE_MAPS_SUBSCRIPTION_KEY not found in environment")
        return False
    
    print(f"✓ Found subscription key: {subscription_key[:10]}...{subscription_key[-4:]}")
    
    # Test 1: Geocoding API (Search Address)
    print("\n📍 Testing Azure Maps Search API (Geocoding)...")
    test_address = "123 Collins St, Melbourne VIC 3000"
    
    search_url = "https://atlas.microsoft.com/search/address/json"
    search_params = {
        'api-version': '1.0',
        'subscription-key': subscription_key,
        'query': test_address
    }
    
    try:
        response = requests.get(search_url, params=search_params, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('results'):
                result = data['results'][0]
                position = result.get('position', {})
                print(f"✅ Geocoding SUCCESS!")
                print(f"   Address: {result.get('address', {}).get('freeformAddress', 'N/A')}")
                print(f"   Coordinates: {position.get('lat')}, {position.get('lon')}")
            else:
                print("⚠️  No results returned")
                return False
        elif response.status_code == 401:
            print("❌ AUTHENTICATION FAILED - Invalid subscription key")
            print(f"   Response: {response.text}")
            return False
        elif response.status_code == 403:
            print("❌ FORBIDDEN - Subscription key may not have permission")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    # Test 2: Route Directions API
    print("\n🗺️  Testing Azure Maps Route API (Directions)...")
    
    route_url = "https://atlas.microsoft.com/route/directions/json"
    route_params = {
        'api-version': '1.0',
        'subscription-key': subscription_key,
        'query': '-37.8136,144.9631:-37.8199,144.9802'  # Melbourne CBD to Federation Square
    }
    
    try:
        response = requests.get(route_url, params=route_params, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('routes'):
                route = data['routes'][0]
                summary = route.get('summary', {})
                distance_km = summary.get('lengthInMeters', 0) / 1000
                duration_min = summary.get('travelTimeInSeconds', 0) / 60
                print(f"✅ Route Directions SUCCESS!")
                print(f"   Distance: {distance_km:.2f} km")
                print(f"   Duration: {duration_min:.1f} minutes")
            else:
                print("⚠️  No route returned")
                return False
        elif response.status_code == 401:
            print("❌ AUTHENTICATION FAILED - Invalid subscription key")
            return False
        elif response.status_code == 403:
            print("❌ FORBIDDEN - Subscription key may not have permission")
            return False
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - Azure Maps subscription key is valid!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_azure_maps_key()
    exit(0 if success else 1)
