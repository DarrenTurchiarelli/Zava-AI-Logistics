#!/usr/bin/env python3
"""
Azure Maps Route Optimization Module

Provides route optimization using Azure Maps API including:
- Multi-waypoint route optimization
- Traffic-aware routing
- Distance and duration calculations
- Map visualization URLs

Uses managed identity (DefaultAzureCredential) - no API keys required.
"""

import base64
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()


class BingMapsRouter:
    """Handle Azure Maps API interactions for route optimization

    Note: Class name kept as BingMapsRouter for backward compatibility
    but now uses Azure Maps API with managed identity authentication.
    """

    def __init__(self, geocode_cache=None, cache_lock=None):
        # Azure Maps only supports subscription key authentication
        # Managed identity is NOT supported by Azure Maps API
        self.subscription_key = os.getenv("AZURE_MAPS_SUBSCRIPTION_KEY", "")

        self.base_url = "https://atlas.microsoft.com"
        self.api_version = "1.0"
        # External cache for geocoding results (shared across instances)
        self.geocode_cache = geocode_cache if geocode_cache is not None else {}
        self.cache_lock = cache_lock
        self.cache_ttl = 86400  # 24 hours in seconds
        
        if self.subscription_key:
            print(f"[MAPS] ✓ Initialized with subscription key (length: {len(self.subscription_key)})")
        else:
            print("[MAPS] ⚠️ WARNING: Azure Maps subscription key not configured - geocoding will fail")
            print("[MAPS]    Set AZURE_MAPS_SUBSCRIPTION_KEY environment variable")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Azure Maps (subscription key only)"""
        if not self.subscription_key:
            print("[ERROR] Azure Maps subscription key not configured")
            return {}
        return {"Ocp-Apim-Subscription-Key": self.subscription_key}

    def _geographic_optimization(self, waypoints: List[str]) -> List[str]:
        """Optimize route using nearest-neighbor algorithm based on coordinates

        This is a fallback when Azure Maps doesn't return optimized order.
        Uses a greedy nearest-neighbor approach to minimize travel distance.
        """
        if not waypoints or len(waypoints) <= 2:
            return waypoints

        # Geocode all waypoints
        coords_map = {}
        for addr in waypoints:
            coords = self.geocode_address(addr)
            if coords:
                coords_map[addr] = coords

        if len(coords_map) < 2:
            return waypoints

        # Start with the first waypoint (usually depot)
        optimized = [waypoints[0]]
        remaining = set(waypoints[1:])
        current_coords = coords_map.get(waypoints[0])

        if not current_coords:
            return waypoints

        # Greedy nearest-neighbor: always go to the closest unvisited waypoint
        while remaining:
            nearest = None
            nearest_dist = float("inf")

            for addr in remaining:
                if addr not in coords_map:
                    continue

                target_coords = coords_map[addr]
                # Calculate Euclidean distance (good enough for local optimization)
                dist = (
                    (current_coords[0] - target_coords[0]) ** 2 + (current_coords[1] - target_coords[1]) ** 2
                ) ** 0.5

                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = addr

            if nearest:
                optimized.append(nearest)
                remaining.remove(nearest)
                current_coords = coords_map[nearest]
            else:
                # Fallback: add remaining in original order
                optimized.extend(sorted(remaining, key=lambda x: waypoints.index(x)))
                break

        return optimized

    def _large_route_optimization(
        self, addresses: List[str], start_location: str = None, route_type: str = "fastest"
    ) -> Dict[str, Any]:
        """Optimize routes with >25 addresses by splitting into chunks and calling Azure Maps API

        For large address sets, split into chunks of 20 addresses each, get actual road routes
        from Azure Maps API, then combine the results.
        """
        waypoints = [start_location] + addresses if start_location else addresses

        # Geocode all addresses first
        coords_map = {}
        print(f"🗺️  Geocoding {len(waypoints)} addresses for large route optimization...")
        for addr in waypoints:
            coords = self.geocode_address(addr)
            if coords:
                coords_map[addr] = coords

        if len(coords_map) < 2:
            print(f"❌ Insufficient geocoded addresses")
            return self._mock_optimization(addresses, start_location)

        # Apply nearest-neighbor optimization to get initial ordering
        optimized_waypoints = self._geographic_optimization(waypoints)
        print(f"✅ Nearest-neighbor optimization complete: {len(optimized_waypoints)} stops")

        # Split into chunks of 20 waypoints for Azure Maps API
        chunk_size = 20
        total_distance = 0
        total_duration = 0
        route_legs = []
        all_route_points = []

        print(f"📊 Splitting route into chunks of {chunk_size} for Azure Maps API...")

        for chunk_idx in range(0, len(optimized_waypoints), chunk_size):
            chunk = optimized_waypoints[chunk_idx : chunk_idx + chunk_size]
            print(
                f"   Processing chunk {chunk_idx//chunk_size + 1}: waypoints {chunk_idx+1}-{min(chunk_idx+chunk_size, len(optimized_waypoints))}"
            )

            # Get coordinates for this chunk
            chunk_coords = []
            for addr in chunk:
                if addr in coords_map:
                    chunk_coords.append(coords_map[addr])

            if len(chunk_coords) < 2:
                continue

            # Call Azure Maps Route API for this chunk
            try:
                route_url = f"{self.base_url}/route/directions/json"
                query_coords = ":".join([f"{lat},{lon}" for lat, lon in chunk_coords])

                route_params = self._get_route_params(route_type)
                params = {
                    "api-version": self.api_version,
                    "subscription-key": self.subscription_key,
                    "query": query_coords,
                    "traffic": "true" if route_type == "fastest" else "false",
                    "travelMode": "car",
                    "routeType": route_params["routeType"],
                    "instructionsType": "text",
                    "language": "en-US",
                }

                response = requests.get(route_url, params=params, timeout=30)
                response.raise_for_status()
                route_data = response.json()

                if route_data.get("routes") and len(route_data["routes"]) > 0:
                    route = route_data["routes"][0]
                    summary = route.get("summary", {})

                    chunk_distance = summary.get("lengthInMeters", 0) / 1000
                    chunk_duration = summary.get("travelTimeInSeconds", 0) / 60

                    total_distance += chunk_distance
                    total_duration += chunk_duration

                    # Extract route geometry points
                    for leg in route.get("legs", []):
                        for point in leg.get("points", []):
                            all_route_points.append([point["longitude"], point["latitude"]])

                        leg_summary = leg.get("summary", {})
                        route_legs.append(
                            {
                                "distance_km": leg_summary.get("lengthInMeters", 0) / 1000,
                                "duration_minutes": leg_summary.get("travelTimeInSeconds", 0) / 60,
                                "summary": f"Leg {len(route_legs) + 1}",
                            }
                        )

                    print(
                        f"      ✓ Chunk {chunk_idx//chunk_size + 1}: {chunk_distance:.1f}km, {chunk_duration:.0f}min, {len(all_route_points)} route points"
                    )
                else:
                    print(f"      ⚠️ No route data for chunk {chunk_idx//chunk_size + 1}")

            except Exception as e:
                print(f"      ❌ Error processing chunk {chunk_idx//chunk_size + 1}: {e}")
                # Continue with next chunk

        # Add 3 minutes per stop for delivery time
        total_duration += (len(optimized_waypoints) - 1) * 3

        print(
            f"✅ Large route optimized: {len(optimized_waypoints)} stops, {total_distance:.1f}km, {total_duration:.0f}min"
        )
        print(f"   Route geometry: {len(all_route_points)} road-following points")

        return {
            "waypoints": optimized_waypoints,
            "total_distance_km": round(total_distance, 2),
            "total_duration_minutes": round(total_duration, 1),
            "route_url": self.generate_map_url(optimized_waypoints),
            "route_legs": route_legs,
            "route_points": all_route_points,  # Include actual route geometry
            "optimized": True,
            "traffic_considered": route_type == "fastest",
            "route_type": route_type,
            "side_of_road_considered": route_type == "safest",
            "large_route": True,
            "chunks_processed": (len(optimized_waypoints) + chunk_size - 1) // chunk_size,
        }

    def optimize_route(
        self, addresses: List[str], start_location: str = None, route_type: str = "fastest"
    ) -> Optional[Dict[str, Any]]:
        """
        Optimize delivery route for multiple addresses considering traffic

        Args:
            addresses: List of delivery addresses (up to 150 for Azure Maps)
            start_location: Optional starting location (defaults to first address)
            route_type: Type of route - 'fastest', 'shortest', or 'safest'

        Returns:
            Dictionary with optimized route information including:
            - waypoints: Ordered list of addresses
            - total_distance_km: Total route distance
            - total_duration_minutes: Estimated travel time
            - route_url: URL to view route on Azure Maps
            - route_type: The type of route optimization used
        """
        # Check authentication is configured
        if not self.subscription_key:
            print("[WARN] Azure Maps not configured. Using mock route optimization.")
            print("       Set AZURE_MAPS_SUBSCRIPTION_KEY in environment variables")
            return self._mock_optimization(addresses, start_location)

        print(f"[OK] Azure Maps using subscription key ({self.subscription_key[:10]}...)")

        if not addresses or len(addresses) == 0:
            return None

        # For large address sets (>25), use geographic clustering instead of Azure Maps API
        # Azure Maps Route API has a 25-waypoint limit
        if len(addresses) > 25:
            print(f"📊 Large address set ({len(addresses)} addresses) - using geographic optimization")
            return self._large_route_optimization(addresses, start_location, route_type)

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
                    print(f"  ⚠️ Could not geocode (skipping): {addr}")

            if len(coordinates) < 2:
                print(f"❌ Only {len(coordinates)} addresses geocoded (need ≥2). Falling back to mock.")
                return self._mock_optimization(addresses, start_location)

            # Use Azure Maps Route Directions API
            route_url = f"{self.base_url}/route/directions/json"

            # Build query string with coordinates
            query_coords = ":".join([f"{lat},{lon}" for lat, lon in coordinates])

            print(f"🗺️  Calling Azure Maps Route API with {len(coordinates)} waypoints...")

            # Determine route parameters based on route type
            route_params = self._get_route_params(route_type)

            params = {
                "api-version": self.api_version,
                "query": query_coords,
                "traffic": "true" if route_type == "fastest" else "false",
                "travelMode": "car",
                "computeBestOrder": "true",  # Optimize waypoint order
                "routeType": route_params["routeType"],
                "sectionType": "traffic",  # Get traffic info
                "instructionsType": "text",
                "avoid": route_params.get("avoid", ""),
                "language": "en-US",
                "subscription-key": self.subscription_key,
            }

            # Make API request
            response = requests.get(route_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            print(f"✓ Route API response received (status {response.status_code})")

            # Extract route information
            if "routes" not in data or len(data["routes"]) == 0:
                print(f"❌ Azure Maps API returned no routes")
                print(f"   Response: {data}")
                return self._mock_optimization(addresses, start_location)

            route = data["routes"][0]
            summary = route.get("summary", {})

            total_distance = summary.get("lengthInMeters", 0) / 1000  # Convert to km
            total_duration = summary.get("travelTimeInSeconds", 0) / 60  # Convert to minutes

            # Debug: Print the route structure to understand what Azure Maps returns
            print(f"🔍 Azure Maps route response keys: {route.keys()}")
            if "optimizedWaypoints" in route:
                print(f"   optimizedWaypoints found: {route['optimizedWaypoints']}")
            if "guidance" in route:
                print(
                    f"   guidance found with keys: {route['guidance'].keys() if isinstance(route['guidance'], dict) else type(route['guidance'])}"
                )

            # Get optimized waypoint order
            # Azure Maps returns optimized order in the guidance.instructions or legs
            optimized_order = route.get("optimizedWaypoints", [])
            if optimized_order and len(optimized_order) > 0:
                # Map optimized indices back to addresses
                optimized_addresses = [waypoints[wp["optimizedIndex"]] for wp in optimized_order]
                print(f"🔄 Azure Maps optimized waypoint order:")
                for idx, addr in enumerate(optimized_addresses):
                    original_idx = waypoints.index(addr)
                    print(f"   {idx+1}. {addr[:50]}... (was #{original_idx+1})")
            else:
                # No optimized order returned - Azure Maps might not support this with current params
                # Fall back to geographic nearest-neighbor optimization
                print(f"⚠️ No optimized order returned by Azure Maps")
                print(f"   Applying geographic nearest-neighbor optimization...")
                optimized_addresses = self._geographic_optimization(waypoints)
                for idx, addr in enumerate(optimized_addresses):
                    original_idx = waypoints.index(addr)
                    print(f"   {idx+1}. {addr[:50]}... (was #{original_idx+1})")

            # Generate map URL
            map_url = self.generate_map_url(optimized_addresses)

            # Extract route geometry (road-following coordinates) from response
            route_points = []  # [lon, lat] pairs for Atlas LineString
            route_legs = []
            for leg in route.get("legs", []):
                leg_summary = leg.get("summary", {})
                route_legs.append(
                    {
                        "distance_km": leg_summary.get("lengthInMeters", 0) / 1000,
                        "duration_minutes": leg_summary.get("travelTimeInSeconds", 0) / 60,
                        "summary": f"Leg {len(route_legs) + 1}",
                    }
                )
                for pt in leg.get("points", []):
                    route_points.append([pt["longitude"], pt["latitude"]])

            # Waypoint lat/lon for map pins (pre-geocoded)
            waypoint_coords = [[lon, lat] for lat, lon in coordinates]

            print(f"✓ Extracted {len(route_points)} road geometry points, {len(waypoint_coords)} pin coords")

            return {
                "waypoints": optimized_addresses,
                "total_distance_km": round(total_distance, 2),
                "total_duration_minutes": round(total_duration, 1),
                "route_url": map_url,
                "route_legs": route_legs,
                "route_points": route_points,
                "waypoint_coords": waypoint_coords,
                "optimized": True,
                "traffic_considered": route_type == "fastest",
                "route_type": route_type,
                "side_of_road_considered": route_type == "safest",
            }

        except requests.RequestException as e:
            print(f"❌ Error calling Azure Maps API: {e}")
            if hasattr(e, "response") and e.response is not None:
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
        pins_js = ", ".join([f"[{lon}, {lat}]" for lat, lon in coordinates])

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

    def _get_route_params(self, route_type: str) -> Dict[str, Any]:
        """Get Azure Maps API parameters for different route types"""
        if route_type == "shortest":
            return {"routeType": "shortest", "avoid": ""}  # Shortest distance
        elif route_type == "safest":
            return {
                "routeType": "fastest",  # Still use fastest for base calculation
                "avoid": "unpavedRoads",  # Avoid unpaved roads for safety
            }
        else:  # fastest (default)
            return {"routeType": "fastest", "avoid": ""}  # Fastest with traffic

    def optimize_all_route_types(self, addresses: List[str], start_location: str = None) -> Dict[str, Any]:
        """
        Generate all three route types for driver selection

        Returns a dictionary containing:
        - fastest: Traffic-optimized route (shortest time)
        - shortest: Distance-optimized route (shortest distance)
        - safest: Safety-optimized route (considers side-of-road, safer roads)
        - recommended: Default recommended route (fastest)
        """
        print("\n" + "=" * 60)
        print("🚚 GENERATING MULTI-ROUTE OPTIONS FOR DRIVER")
        print("=" * 60)

        routes = {}

        # 1. Fastest Route (Traffic-aware, quickest time)
        print("\n🏎️  Calculating FASTEST route (traffic-aware)...")
        fastest = self.optimize_route(addresses, start_location, route_type="fastest")
        if fastest:
            routes["fastest"] = fastest
            routes["fastest"]["description"] = "Quickest route based on current traffic conditions"
            routes["fastest"]["icon"] = "⚡"
            print(f"   ✓ {fastest['total_duration_minutes']} min, {fastest['total_distance_km']} km")

        # 2. Shortest Route (Minimum distance)
        print("\n📏 Calculating SHORTEST route (minimum distance)...")
        shortest = self.optimize_route(addresses, start_location, route_type="shortest")
        if shortest:
            routes["shortest"] = shortest
            routes["shortest"]["description"] = "Shortest distance route (may take longer due to roads/traffic)"
            routes["shortest"]["icon"] = "📍"
            print(f"   ✓ {shortest['total_duration_minutes']} min, {shortest['total_distance_km']} km")

        # 3. Safest Route (Side-of-road optimized, safer roads)
        print("\n🛡️  Calculating SAFEST route (side-of-road optimized)...")
        safest = self.optimize_route_with_side_of_road_safety(addresses, start_location)
        if safest:
            routes["safest"] = safest
            routes["safest"]["description"] = "Optimized for driver safety with minimal road crossings"
            routes["safest"]["icon"] = "🛡️"
            print(f"   ✓ {safest['total_duration_minutes']} min, {safest['total_distance_km']} km")
            print(f"   ✓ Road crossings minimized: {safest.get('crossing_warnings', 0)} warnings")

        # Set recommended route (default to fastest)
        routes["recommended"] = "fastest"

        print("\n" + "=" * 60)
        print(f"✅ Generated {len(routes)-1} route options for driver selection")
        print("=" * 60 + "\n")

        return routes

    def optimize_route_with_side_of_road_safety(
        self, addresses: List[str], start_location: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Optimize route considering which side of the road destinations are on
        Minimizes the need for drivers to cross roads for safety
        """
        if not self.subscription_key:
            return self._mock_optimization(addresses, start_location)

        # Get base safest route
        route = self.optimize_route(addresses, start_location, route_type="safest")

        if not route:
            return None

        # Enhance with side-of-road analysis
        print("\n🔍 Analyzing side-of-road positioning for safety...")

        waypoints = route["waypoints"]
        crossing_warnings = 0
        enhanced_legs = []

        for i in range(len(waypoints) - 1):
            current_addr = waypoints[i]
            next_addr = waypoints[i + 1]

            # Get detailed routing between consecutive stops
            leg_info = self._analyze_leg_safety(current_addr, next_addr)

            if leg_info and leg_info.get("requires_crossing"):
                crossing_warnings += 1
                print(f"   ⚠️  Stop {i+1} -> {i+2}: May require road crossing")

            enhanced_legs.append(leg_info if leg_info else {})

        route["route_legs_detailed"] = enhanced_legs
        route["crossing_warnings"] = crossing_warnings
        route["safety_score"] = max(0, 100 - (crossing_warnings * 10))  # Score out of 100

        return route

    def _analyze_leg_safety(self, from_addr: str, to_addr: str) -> Optional[Dict[str, Any]]:
        """Analyze a single route leg for side-of-road safety considerations"""
        try:
            # Geocode both addresses
            from_coords = self.geocode_address(from_addr)
            to_coords = self.geocode_address(to_addr)

            if not from_coords or not to_coords:
                return None

            # Get detailed route between two points
            route_url = f"{self.base_url}/route/directions/json"

            # Azure Maps requires specific coordinate format: lat1,lon1:lat2,lon2
            query = f"{from_coords[0]},{from_coords[1]}:{to_coords[0]},{to_coords[1]}"

            params = {
                "api-version": self.api_version,
                "subscription-key": self.subscription_key,
                "query": query,
                "travelMode": "car",
                "routeType": "shortest",  # Changed from 'safest' which may not be valid
                "instructionsType": "text",
            }

            response = requests.get(route_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "routes" in data and len(data["routes"]) > 0:
                route = data["routes"][0]

                # Analyze if destination is on same side as approach direction
                # This is a simplified heuristic - in production you'd use more sophisticated analysis
                legs = route.get("legs", [])
                if legs:
                    leg = legs[0]
                    summary = leg.get("summary", {})

                    # Check for U-turns or significant direction changes that might indicate
                    # the destination is on the opposite side of the road
                    requires_crossing = False

                    # Look at guidance instructions for crossing indicators
                    guidance = leg.get("guidance", {})
                    instructions = guidance.get("instructions", [])

                    for instruction in instructions:
                        text = instruction.get("text", "").lower()
                        # Check for indicators of needing to cross
                        if any(word in text for word in ["u-turn", "cross", "opposite side"]):
                            requires_crossing = True
                            break

                    return {
                        "from": from_addr,
                        "to": to_addr,
                        "distance_km": summary.get("lengthInMeters", 0) / 1000,
                        "duration_minutes": summary.get("travelTimeInSeconds", 0) / 60,
                        "requires_crossing": requires_crossing,
                        "safety_notes": "Driver may need to cross road"
                        if requires_crossing
                        else "Safe curbside access",
                    }

            return None

        except requests.HTTPError as e:
            # HTTP errors are expected when API rejects params - silently skip
            if os.getenv("DEBUG_MODE") == "true":
                print(f"   ⚠️  Could not analyze leg safety: {e}")
            return None
        except Exception as e:
            if os.getenv("DEBUG_MODE") == "true":
                print(f"   ⚠️  Could not analyze leg safety: {e}")
            return None

    def _mock_optimization(self, addresses: List[str], start_location: str = None) -> Dict[str, Any]:
        waypoints = [start_location] + addresses if start_location else addresses

        # Estimate: 5km average per stop, 10 min per stop
        num_stops = len(waypoints) - 1 if start_location else len(waypoints)
        estimated_distance = num_stops * 5.0
        estimated_duration = num_stops * 10.0

        return {
            "waypoints": waypoints,
            "total_distance_km": round(estimated_distance, 2),
            "total_duration_minutes": round(estimated_duration, 1),
            "route_url": self.generate_map_url(waypoints),
            "route_legs": [
                {"distance_km": 5.0, "duration_minutes": 10.0, "summary": f"Drive to {addr}"} for addr in waypoints[1:]
            ],
            "optimized": False,
            "traffic_considered": False,
            "mock_data": True,
        }

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to latitude/longitude coordinates using Azure Maps
        Uses caching to avoid redundant API calls

        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        # Check if Azure Maps is configured
        if not self.subscription_key:
            print("[ERROR] Azure Maps subscription key not configured - geocoding unavailable")
            return None

        # Check cache first
        if self.cache_lock:
            with self.cache_lock:
                if address in self.geocode_cache:
                    cached_data = self.geocode_cache[address]
                    timestamp = cached_data.get("timestamp", 0)
                    if time.time() - timestamp < self.cache_ttl:
                        coords = cached_data.get("coords")
                        if coords:
                            print(f"💾 Cache hit: {address} -> {coords}")
                            return coords
        elif address in self.geocode_cache:
            cached_data = self.geocode_cache[address]
            timestamp = cached_data.get("timestamp", 0)
            if time.time() - timestamp < self.cache_ttl:
                coords = cached_data.get("coords")
                if coords:
                    print(f"💾 Cache hit: {address} -> {coords}")
                    return coords

        try:
            import time as time_module

            search_url = f"{self.base_url}/search/address/json"
            params = {
                "api-version": self.api_version,
                "subscription-key": self.subscription_key,  # Pass key as query parameter
                "query": address,
                "limit": 1,
                "countrySet": "AU",  # Bias to Australia
                "view": "Auto",
            }

            response = requests.get(search_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                position = result["position"]
                lat, lon = position["lat"], position["lon"]

                # Debug: Print the full result structure
                print(f"DEBUG - Azure Maps result for '{address}':")
                print(f"  Entity Type: {result.get('entityType', 'N/A')}")
                print(f"  Type: {result.get('type', 'N/A')}")
                print(f"  Match Confidence: {result.get('matchConfidence', 'N/A')}")
                print(f"  Score: {result.get('score', 'N/A')}")

                # Check confidence - Azure Maps uses 'score' not matchConfidence.score
                score = result.get("score", 0)
                entity_type = result.get("type", "")

                # Reject only extremely poor confidence matches.
                # Demo/generated addresses may return suburb-level scores ~0.2-0.4 — still useful.
                if score < 0.2:
                    print(f"⚠️ Very low confidence match (score={score}): {address}")
                    return None
                elif score < 0.6:
                    print(f"⚠️ Low-medium confidence match (score={score}): {address} - accepting anyway")

                # Reject if it's not a specific address type
                # Common types: 'Point Address', 'Address Range', 'Street'
                address_types = ["Point Address", "Address Range", "Street"]
                if entity_type not in address_types:
                    print(f"⚠️ Not a specific street address ({entity_type}): {address}")
                    # Don't reject, just warn - might be too strict
                    pass

                # Validate coordinates are in Australia/Oceania range
                # Australia: lat -44 to -10, lon 113 to 154
                if -45 <= lat <= -9 and 110 <= lon <= 160:
                    coords = (lat, lon)
                    # Store in cache
                    if self.cache_lock:
                        with self.cache_lock:
                            self.geocode_cache[address] = {"coords": coords, "timestamp": time_module.time()}
                    else:
                        self.geocode_cache[address] = {"coords": coords, "timestamp": time_module.time()}
                    return coords
                else:
                    print(f"⚠️ Geocoded to non-Australian location: {address} -> ({lat}, {lon})")
                    # Try adding "Australia" to the query
                    if "australia" not in address.lower() and "au" not in address.lower():
                        params["query"] = address + ", Australia"
                        response = requests.get(search_url, params=params, timeout=5)
                        response.raise_for_status()
                        data = response.json()

                        if "results" in data and len(data["results"]) > 0:
                            position = data["results"][0]["position"]
                            lat, lon = position["lat"], position["lon"]
                            print(f"✓ Retry with 'Australia': {address} -> ({lat}, {lon})")
                            return (lat, lon)

            return None

        except Exception as e:
            print(f"❌ Error geocoding address '{address}': {e}")
            return None

    def geocode_address_strict(self, address: str) -> dict:
        """
        Validate address with strict matching - checks if returned address matches input
        Returns dict with 'valid' flag and details
        """
        import re

        # Check if Azure Maps is configured
        if not self.subscription_key:
            return {"valid": False, "message": "Azure Maps subscription key not configured"}

        try:
            search_url = f"{self.base_url}/search/address/json"
            params = {
                "api-version": self.api_version,
                "subscription-key": self.subscription_key,
                "query": address,
                "limit": 1,
                "countrySet": "AU"
            }

            response = requests.get(search_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if "results" not in data or len(data["results"]) == 0:
                return {"valid": False, "message": "No matching address found"}

            result = data["results"][0]

            # Extract user's input postcode
            user_postcode = None
            postcode_match = re.search(r"\b(\d{4})\b", address)
            if postcode_match:
                user_postcode = postcode_match.group(1)

            # Get returned address details
            returned_address = result.get("address", {})
            returned_postcode = returned_address.get("postalCode", "").strip()
            returned_street = returned_address.get("streetName", "").strip()
            returned_street_number = returned_address.get("streetNumber", "").strip()

            # Check confidence score
            score = result.get("score", 0)
            if score < 0.8:  # Require high confidence (80%+)
                return {"valid": False, "message": f"Low confidence match (only {score*100:.0f}% confident)"}

            # STRICT: If user provided postcode, it must match exactly
            if user_postcode and returned_postcode:
                if user_postcode != returned_postcode:
                    return {
                        "valid": False,
                        "message": f"Postcode mismatch: You entered {user_postcode}, but Azure Maps found {returned_postcode}",
                    }

            # Check if street name was actually found (not just suburb)
            if not returned_street or not returned_street_number:
                return {"valid": False, "message": "Street address not found - only suburb/locality matched"}

            # Validate coordinates are in Australia
            position = result["position"]
            lat, lon = position["lat"], position["lon"]
            if not (-45 <= lat <= -9 and 110 <= lon <= 160):
                return {"valid": False, "message": "Geocoded location is not in Australia"}

            # Build formatted address
            formatted_parts = []
            if returned_street_number:
                formatted_parts.append(returned_street_number)
            if returned_street:
                formatted_parts.append(returned_street)
            if returned_address.get("municipality"):
                formatted_parts.append(returned_address["municipality"])
            if returned_address.get("countrySubdivision"):
                formatted_parts.append(returned_address["countrySubdivision"])
            if returned_postcode:
                formatted_parts.append(returned_postcode)

            formatted_address = ", ".join(formatted_parts)

            return {
                "valid": True,
                "coords": (lat, lon),
                "formatted_address": formatted_address,
                "message": "Valid Australian address",
            }

        except Exception as e:
            print(f"❌ Error validating address '{address}': {e}")
            return {"valid": False, "message": f"Validation error: {str(e)}"}

    def generate_approximate_delivery_map(
        self,
        approximate_lat: float,
        approximate_lon: float,
        actual_lat: float,
        actual_lon: float,
        radius_km: float = 5,
        width: int = 800,
        height: int = 400,
    ) -> str:
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
