#!/usr/bin/env python3
"""
Azure Maps Route Optimization Module

Provides route optimization using Azure Maps API including:
- Multi-waypoint route optimization
- Traffic-aware routing
- Distance and duration calculations
- Map visualization URLs

Migrated from Bing Maps (deprecated) to Azure Maps
"""

import os
import requests
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class BingMapsRouter:
    """Handle Azure Maps API interactions for route optimization
    
    Note: Class name kept as BingMapsRouter for backward compatibility
    but now uses Azure Maps API
    """
    
    def __init__(self):
        self.subscription_key = os.getenv('AZURE_MAPS_SUBSCRIPTION_KEY', '')
        self.base_url = "https://atlas.microsoft.com"
        self.api_version = "1.0"
        
    def optimize_route(self, addresses: List[str], start_location: str = None) -> Optional[Dict[str, Any]]:
        """
        Optimize delivery route for multiple addresses considering traffic
        
        Args:
            addresses: List of delivery addresses (up to 150 for Azure Maps)
            start_location: Optional starting location (defaults to first address)
            
        Returns:
            Dictionary with optimized route information including:
            - waypoints: Ordered list of addresses
            - total_distance_km: Total route distance
            - total_duration_minutes: Estimated travel time
            - route_url: URL to view route on Azure Maps
        """
        if not self.subscription_key:
            print("⚠️ AZURE_MAPS_SUBSCRIPTION_KEY not configured. Using mock route optimization.")
            return self._mock_optimization(addresses, start_location)
        
        if not addresses or len(addresses) == 0:
            return None
            
        if len(addresses) > 20:
            print(f"⚠️ Route limited to 20 waypoints for optimal performance.")
            addresses = addresses[:20]
        
        try:
            # First, geocode all addresses to get coordinates
            waypoints = [start_location] + addresses if start_location else addresses
            coordinates = []
            
            for addr in waypoints:
                coords = self.geocode_address(addr)
                if coords:
                    coordinates.append(coords)
                else:
                    print(f"⚠️ Could not geocode address: {addr}")
                    return self._mock_optimization(addresses, start_location)
            
            # Use Azure Maps Route Directions API
            route_url = f"{self.base_url}/route/directions/json"
            
            # Build query string with coordinates
            query_coords = ":".join([f"{lat},{lon}" for lat, lon in coordinates])
            
            params = {
                'api-version': self.api_version,
                'subscription-key': self.subscription_key,
                'query': query_coords,
                'traffic': 'true',  # Consider real-time traffic
                'travelMode': 'car',
                'computeBestOrder': 'true',  # Optimize waypoint order
                'routeType': 'fastest',  # Fastest route considering traffic
                'language': 'en-US'
            }
            
            # Make API request
            response = requests.get(route_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract route information
            if 'routes' not in data or len(data['routes']) == 0:
                print(f"❌ Azure Maps API returned no routes")
                return self._mock_optimization(addresses, start_location)
            
            route = data['routes'][0]
            summary = route.get('summary', {})
            
            total_distance = summary.get('lengthInMeters', 0) / 1000  # Convert to km
            total_duration = summary.get('travelTimeInSeconds', 0) / 60  # Convert to minutes
            
            # Get optimized waypoint order
            optimized_order = route.get('optimizedWaypoints', [])
            if optimized_order:
                # Map optimized indices back to addresses
                optimized_addresses = [waypoints[wp['optimizedIndex']] for wp in optimized_order]
            else:
                optimized_addresses = waypoints
            
            # Generate map URL
            map_url = self.generate_map_url(optimized_addresses)
            
            # Build detailed route with individual legs
            route_legs = []
            for leg in route.get('legs', []):
                leg_summary = leg.get('summary', {})
                route_legs.append({
                    'distance_km': leg_summary.get('lengthInMeters', 0) / 1000,
                    'duration_minutes': leg_summary.get('travelTimeInSeconds', 0) / 60,
                    'summary': f"Leg {len(route_legs) + 1}"
                })
            
            return {
                'waypoints': optimized_addresses,
                'total_distance_km': round(total_distance, 2),
                'total_duration_minutes': round(total_duration, 1),
                'route_url': map_url,
                'route_legs': route_legs,
                'optimized': True,
                'traffic_considered': True
            }
            
        except requests.RequestException as e:
            print(f"❌ Error calling Azure Maps API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return self._mock_optimization(addresses, start_location)
        except Exception as e:
            print(f"❌ Error optimizing route: {e}")
            return self._mock_optimization(addresses, start_location)
    
    def generate_map_url(self, addresses: List[str]) -> str:
        """Generate an Azure Maps URL to display the route"""
        if not addresses:
            return ""
        
        # Azure Maps doesn't have a simple web URL like Bing Maps
        # Return a URL that will open Azure Maps with the first address
        first_addr = addresses[0] if addresses else "Sydney, Australia"
        return f"https://azure.microsoft.com/en-us/products/azure-maps/"
    
    def generate_embed_url(self, addresses: List[str], width: int = 800, height: int = 600) -> str:
        """Generate an embeddable Azure Maps iframe URL using Web SDK"""
        if not self.subscription_key or not addresses:
            return ""
        
        # For Azure Maps, we need to use the Web SDK with HTML/JavaScript
        # This returns a data URL that can be embedded
        # In production, you should serve this from your own endpoint
        
        # Create HTML with Azure Maps Web SDK
        coordinates = []
        for addr in addresses:
            coords = self.geocode_address(addr)
            if coords:
                coordinates.append(coords)
                print(f"📍 Geocoded: {addr} -> {coords}")
            else:
                print(f"❌ Failed to geocode: {addr}")
        
        if not coordinates:
            print("❌ No coordinates generated for embed URL")
            return ""
        
        # Use first coordinate as the center (driver's starting point)
        center_lat, center_lon = coordinates[0]
        print(f"🗺️  Map center: lat={center_lat}, lon={center_lon}")
        print(f"🗺️  Total stops: {len(coordinates)}")
        
        # Generate inline HTML with Azure Maps
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.css" />
    <script src="https://atlas.microsoft.com/sdk/javascript/mapcontrol/2/atlas.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ width: 100%; height: {height}px; opacity: 0; transition: opacity 0.3s; }}
        #map.ready {{ opacity: 1; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        // Define center coordinates
        var centerLon = {center_lon};
        var centerLat = {center_lat};
        
        console.log('Map initialization - Center: [' + centerLon + ', ' + centerLat + '], Zoom: 11');
        
        var map = new atlas.Map('map', {{
            center: [centerLon, centerLat],
            zoom: 11,
            language: 'en-US',
            renderWorldCopies: false,
            style: 'road',
            authOptions: {{
                authType: 'subscriptionKey',
                subscriptionKey: '{self.subscription_key}'
            }}
        }});
        
        console.log('Map object created, waiting for ready event...');
        
        map.events.add('ready', function() {{
            console.log('Map ready event fired');
            var dataSource = new atlas.source.DataSource();
            map.sources.add(dataSource);
            
            // Add markers for each delivery
            var pins = [{', '.join([f"[{lon}, {lat}]" for lat, lon in coordinates])}];
            
            // Add all pins to data source
            pins.forEach(function(pin, index) {{
                dataSource.add(new atlas.data.Feature(new atlas.data.Point(pin), {{
                    title: 'Stop ' + (index + 1),
                    isWaypoint: true
                }}));
            }});
            
            // Add numbered markers
            map.layers.add(new atlas.layer.SymbolLayer(dataSource, null, {{
                filter: ['==', ['get', 'isWaypoint'], true],
                iconOptions: {{
                    image: 'marker-blue',
                    size: 0.8
                }},
                textOptions: {{
                    textField: ['get', 'title'],
                    offset: [0, -2.5],
                    color: '#ffffff',
                    size: 12
                }}
            }}));
            
            // Fetch and draw the route between waypoints
            var coordinates = [{', '.join([f"'{lat},{lon}'" for lat, lon in coordinates])}];
            var routeUrl = 'https://atlas.microsoft.com/route/directions/json?api-version=1.0&subscription-key={self.subscription_key}&query=' + coordinates.join(':');
            
            fetch(routeUrl)
                .then(response => response.json())
                .then(data => {{
                    if (data.routes && data.routes.length > 0) {{
                        var route = data.routes[0];
                        var routeCoordinates = [];
                        
                        // Extract coordinates from route legs
                        route.legs.forEach(function(leg) {{
                            leg.points.forEach(function(point) {{
                                routeCoordinates.push([point.longitude, point.latitude]);
                            }});
                        }});
                        
                        // Add route line to map
                        dataSource.add(new atlas.data.Feature(new atlas.data.LineString(routeCoordinates)));
                        
                        // Add line layer for the route
                        map.layers.add(new atlas.layer.LineLayer(dataSource, null, {{
                            strokeColor: '#2196F3',
                            strokeWidth: 4,
                            lineJoin: 'round',
                            lineCap: 'round'
                        }}), 'labels');
                        
                        // Don't change camera - keep initial zoom level focused on first delivery
                    }}
                    
                    // Show map once everything is loaded
                    document.getElementById('map').classList.add('ready');
                }})
                .catch(function(err) {{ 
                    console.error('Route fetch error:', err);
                    // Show map even if route fails
                    document.getElementById('map').classList.add('ready');
                }});
        }});
    </script>
</body>
</html>
        """
        
        # Return as data URL for iframe embedding
        import base64
        encoded = base64.b64encode(html_content.encode()).decode()
        return f"data:text/html;base64,{encoded}"
    
    def _mock_optimization(self, addresses: List[str], start_location: str = None) -> Dict[str, Any]:
        """Mock route optimization for testing without API key"""
        waypoints = [start_location] + addresses if start_location else addresses
        
        # Estimate: 5km average per stop, 10 min per stop
        num_stops = len(waypoints) - 1 if start_location else len(waypoints)
        estimated_distance = num_stops * 5.0
        estimated_duration = num_stops * 10.0
        
        return {
            'waypoints': waypoints,
            'total_distance_km': round(estimated_distance, 2),
            'total_duration_minutes': round(estimated_duration, 1),
            'route_url': self.generate_map_url(waypoints),
            'route_legs': [
                {
                    'distance_km': 5.0,
                    'duration_minutes': 10.0,
                    'summary': f'Drive to {addr}'
                } for addr in waypoints[1:]
            ],
            'optimized': False,
            'traffic_considered': False,
            'mock_data': True
        }
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to latitude/longitude coordinates using Azure Maps
        
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        if not self.subscription_key:
            return None
        
        try:
            search_url = f"{self.base_url}/search/address/json"
            params = {
                'api-version': self.api_version,
                'subscription-key': self.subscription_key,
                'query': address,
                'limit': 1
            }
            
            response = requests.get(search_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'results' in data and len(data['results']) > 0:
                position = data['results'][0]['position']
                return (position['lat'], position['lon'])
            
            return None
            
        except Exception as e:
            print(f"❌ Error geocoding address '{address}': {e}")
            return None


# Convenience function for quick route optimization
def get_optimized_route(addresses: List[str], start_location: str = None) -> Optional[Dict[str, Any]]:
    """Quick route optimization helper function"""
    router = BingMapsRouter()
    return router.optimize_route(addresses, start_location)
