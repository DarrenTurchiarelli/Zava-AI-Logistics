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
import base64
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
        
        print(f"✓ Azure Maps key configured: {self.subscription_key[:10]}...")
        
        if not addresses or len(addresses) == 0:
            return None
            
        if len(addresses) > 20:
            print(f"⚠️ Route limited to 20 waypoints for optimal performance.")
            addresses = addresses[:20]
        
        try:
            # First, geocode all addresses to get coordinates
            waypoints = [start_location] + addresses if start_location else addresses
            coordinates = []
            
            print(f"🗺️  Geocoding {len(waypoints)} addresses for route optimization...")
            for addr in waypoints:
                coords = self.geocode_address(addr)
                if coords:
                    coordinates.append(coords)
                    print(f"  ✓ {addr} -> {coords}")
                else:
                    print(f"  ❌ Could not geocode address: {addr}")
                    print(f"⚠️ Falling back to mock optimization due to geocoding failure")
                    return self._mock_optimization(addresses, start_location)
            
            # Use Azure Maps Route Directions API
            route_url = f"{self.base_url}/route/directions/json"
            
            # Build query string with coordinates
            query_coords = ":".join([f"{lat},{lon}" for lat, lon in coordinates])
            
            print(f"🗺️  Calling Azure Maps Route API with {len(coordinates)} waypoints...")
            
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
            
            print(f"✓ Route API response received (status {response.status_code})")
            
            # Extract route information
            if 'routes' not in data or len(data['routes']) == 0:
                print(f"❌ Azure Maps API returned no routes")
                print(f"   Response: {data}")
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
        
        # Create JavaScript array of coordinates
        pins_js = ', '.join([f"[{lon}, {lat}]" for lat, lon in coordinates])
        
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
        #map {{ width: 100%; height: {height}px; }}
        #debug {{ position: absolute; top: 10px; left: 10px; background: white; padding: 10px; 
                 border: 2px solid #333; z-index: 1000; font-family: monospace; font-size: 12px; }}
    </style>
</head>
<body>
    <div id="debug">Loading map...</div>
    <div id="map"></div>
    <script>
        var debugEl = document.getElementById('debug');
        function log(msg) {{
            console.log(msg);
            debugEl.innerHTML += '<br>' + msg;
        }}
        
        // Define center coordinates
        var centerLon = {center_lon};
        var centerLat = {center_lat};
        var pins = [{pins_js}];
        
        log('Initializing map at [' + centerLon + ', ' + centerLat + ']');
        log('Number of waypoints: ' + pins.length);
        
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
        
        map.events.add('ready', function() {{
            log('Map ready!');
            var dataSource = new atlas.source.DataSource();
            map.sources.add(dataSource);
            
            // Add markers for each delivery
            
            // Add all pins to data source
            pins.forEach(function(pin, index) {{
                var point = new atlas.data.Feature(new atlas.data.Point(pin), {{
                    title: 'Stop ' + (index + 1),
                    isWaypoint: true
                }});
                dataSource.add(point);
                log('Added pin ' + (index + 1) + ' at ' + pin);
            }});
            
            log('Added ' + pins.length + ' pins to data source');
            
            // Add numbered markers layer FIRST
            var markerLayer = new atlas.layer.SymbolLayer(dataSource, null, {{
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
            }});
            map.layers.add(markerLayer);
            log('Marker layer added');
            
            // Draw simple line connecting all waypoints
            if (pins.length > 1) {{
                var routeLine = new atlas.data.Feature(
                    new atlas.data.LineString(pins), 
                    {{ isRoute: true }}
                );
                dataSource.add(routeLine);
                
                var lineLayer = new atlas.layer.LineLayer(dataSource, null, {{
                    filter: ['==', ['get', 'isRoute'], true],
                    strokeColor: '#2196F3',
                    strokeWidth: 5,
                    lineJoin: 'round',
                    lineCap: 'round'
                }});
                map.layers.add(lineLayer, markerLayer.getId());
                log('Route line added (simple waypoint connection)');
            }}
            
            // Now try to fetch optimized route from Azure Maps
            if (pins.length > 1) {{
                var coordinates = [{', '.join([f"'{lat},{lon}'" for lat, lon in coordinates])}];
                var routeUrl = 'https://atlas.microsoft.com/route/directions/json?api-version=1.0&subscription-key={self.subscription_key}&query=' + coordinates.join(':') + '&routeRepresentation=polyline';
                
                log('Fetching optimized route...');
                
                fetch(routeUrl)
                    .then(response => {{
                        if (!response.ok) {{
                            throw new Error('HTTP ' + response.status);
                        }}
                        return response.json();
                    }})
                    .then(data => {{
                        if (data.routes && data.routes.length > 0) {{
                            var route = data.routes[0];
                            var routeCoordinates = [];
                            
                            // Extract coordinates from guidance instructions
                            route.legs.forEach(function(leg) {{
                                if (leg.guidance && leg.guidance.instructions) {{
                                    leg.guidance.instructions.forEach(function(instruction) {{
                                        if (instruction.point && instruction.point.latitude && instruction.point.longitude) {{
                                            routeCoordinates.push([instruction.point.longitude, instruction.point.latitude]);
                                        }}
                                    }});
                                }}
                            }});
                            
                            if (routeCoordinates.length > 1) {{
                                // Remove old simple line
                                map.layers.remove(lineLayer);
                                
                                // Add optimized route line
                                var optimizedLine = new atlas.data.Feature(
                                    new atlas.data.LineString(routeCoordinates), 
                                    {{ isRoute: true }}
                                );
                                dataSource.add(optimizedLine);
                                
                                lineLayer = new atlas.layer.LineLayer(dataSource, null, {{
                                    filter: ['==', ['get', 'isRoute'], true],
                                    strokeColor: '#2196F3',
                                    strokeWidth: 5,
                                    lineJoin: 'round',
                                    lineCap: 'round'
                                }});
                                map.layers.add(lineLayer, markerLayer.getId());
                                
                                log('✓ Optimized route loaded (' + routeCoordinates.length + ' points)');
                            }} else {{
                                log('Using simple route (no detailed path available)');
                            }}
                        }}
                    }})
                    .catch(function(err) {{
                        log('Route API error: ' + err.message);
                    }});
            }}
            
            // Hide debug after 3 seconds
            setTimeout(function() {{
                debugEl.style.display = 'none';
            }}, 3000);
        }});
        
        map.events.add('error', function(e) {{
            log('Map error: ' + e.error.message);
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
                'limit': 1,
                'countrySet': 'AU',  # Bias to Australia
                'view': 'Auto'
            }
            
            response = requests.get(search_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'results' in data and len(data['results']) > 0:
                position = data['results'][0]['position']
                lat, lon = position['lat'], position['lon']
                
                # Validate coordinates are in Australia/Oceania range
                # Australia: lat -44 to -10, lon 113 to 154
                if -45 <= lat <= -9 and 110 <= lon <= 160:
                    return (lat, lon)
                else:
                    print(f"⚠️ Geocoded to non-Australian location: {address} -> ({lat}, {lon})")
                    # Try adding "Australia" to the query
                    if "australia" not in address.lower() and "au" not in address.lower():
                        params['query'] = address + ", Australia"
                        response = requests.get(search_url, params=params, timeout=5)
                        response.raise_for_status()
                        data = response.json()
                        
                        if 'results' in data and len(data['results']) > 0:
                            position = data['results'][0]['position']
                            lat, lon = position['lat'], position['lon']
                            print(f"✓ Retry with 'Australia': {address} -> ({lat}, {lon})")
                            return (lat, lon)
            
            return None
            
        except Exception as e:
            print(f"❌ Error geocoding address '{address}': {e}")
            return None

    def generate_approximate_delivery_map(self, approximate_lat: float, approximate_lon: float,
                                         actual_lat: float, actual_lon: float, radius_km: float = 5,
                                         width: int = 800, height: int = 400) -> str:
        """Generate customer-facing delivery map with approximate location for privacy"""
        if not self.subscription_key:
            return ""
        
        # Calculate radius in meters
        radius_m = radius_km * 1000
        
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
        #map {{ width: 100%; height: {height}px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = new atlas.Map('map', {{
            center: [{approximate_lon}, {approximate_lat}],
            zoom: 13,
            language: 'en-US',
            renderWorldCopies: false,
            style: 'road',
            authOptions: {{
                authType: 'subscriptionKey',
                subscriptionKey: '{self.subscription_key}'
            }}
        }});
        
        map.events.add('ready', function() {{
            var dataSource = new atlas.source.DataSource();
            map.sources.add(dataSource);
            
            // Add delivery area circle (5km radius around actual location)
            var circle = new atlas.data.Feature(new atlas.data.Point([{actual_lon}, {actual_lat}]), {{
                subType: "Circle",
                radius: {radius_m}
            }});
            dataSource.add(circle);
            
            // Add circle layer
            map.layers.add(new atlas.layer.PolygonLayer(dataSource, null, {{
                fillColor: '#00a2ff',
                fillOpacity: 0.2,
                strokeColor: '#0078D4',
                strokeWidth: 2
            }}));
            
            // Add truck icon at approximate location
            var truckIcon = new atlas.data.Feature(new atlas.data.Point([{approximate_lon}, {approximate_lat}]), {{
                title: 'Delivery Vehicle'
            }});
            dataSource.add(truckIcon);
            
            // Add truck symbol
            map.layers.add(new atlas.layer.SymbolLayer(dataSource, null, {{
                filter: ['==', ['get', 'title'], 'Delivery Vehicle'],
                iconOptions: {{
                    image: 'pin-blue',
                    size: 1.2
                }},
                textOptions: {{
                    textField: ['get', 'title'],
                    offset: [0, -2.5],
                    color: '#0078D4',
                    size: 12
                }}
            }}));
        }});
    </script>
</body>
</html>
        """
        
        # Return as data URL for iframe embedding
        encoded = base64.b64encode(html_content.encode()).decode()
        return f"data:text/html;base64,{encoded}"


# Convenience function for quick route optimization
def get_optimized_route(addresses: List[str], start_location: str = None) -> Optional[Dict[str, Any]]:
    """Quick route optimization helper function"""
    router = BingMapsRouter()
    return router.optimize_route(addresses, start_location)
